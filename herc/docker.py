import requests
from tornado.web import HTTPError
from . import config
from . import async
import threading
import json
import base64

def construct_docker():
    return DockerTools()
dockerdict = async.ThreadedDict(construct_docker)

@async.usepool('docker')
def verify_image(imageid):
    dockerdict.get().verify_image(imageid)

class DockerTools(object):
    tokens = dict()
    def __init__(self):
        self.session = requests.session()
        self.hubAPI = config.get("docker.hubAPI").rstrip('/')
        self.regAPI = config.get("docker.regAPI").rstrip('/')

        #read our creds from .dockercfg file
        with open(config.get("docker.cfgpath"), 'r') as dockercfg:
            cfg = json.load(dockercfg)
            auth = base64.b64decode( cfg[self.hubAPI+'/']['auth'] ).decode()
            self.service_user, self.service_pass = auth.split(':', maxsplit=1)

    @staticmethod
    def parse_docker_string(imageid):
        """Parses out user/image:tag from a string.
        Note that this doesn't handle horrible things like foo:/bar
        But Docker will 404 if you do something atrocious like that."""
        splitusr = imageid.split('/')
        if len(splitusr) > 2:
            raise HTTPError(400, "Docker image {imageid} is malformed".format(imageid=imageid))
        user = 'library' if len(splitusr) == 1 else splitusr[0]

        splittag = splitusr[-1].split(':')
        if len(splittag) > 2:
            raise HTTPError(400, "Docker image {imageid} is malformed".format(imageid=imageid))
        repo = splittag[0]
        tag = 'latest' if len(splittag) == 1 else splittag[-1]

        return user, repo, tag

    def _token_request(self, user, repo):
        return self.session.get(self.hubAPI + "/repositories/{user}/{repo}/images".format(user=user, repo=repo),
                                auth=(self.service_user, self.service_pass),
                                headers={"X-Docker-Token":"true"})

    def _get_token(self, user, repo, force_new=False):
        """Gets a token used for auth'd requests to Docker Registry.
        It looks something like this, not that you care:
        'signature=f387ad51d64507221adc97ab1e27e919b5ddaa23,repository="user/repo",access=read' """
        try:
            if not force_new:
                return DockerTools.tokens[user+'/'+repo], False
        except KeyError:
            pass  # we'll generate a new token if we haven't returned already

        # Generate a new token by querying DockerHub for the image, and passing X-Docker-Token in the header
        r = self._token_request(user, repo)

        if r.status_code == 404:
            raise HTTPError(400, "Docker image {user}/{repo} not found".format(user=user, repo=repo))
        else:
            r.raise_for_status()  # this will force something weird like a 500 to bubble up to the user

        # Docker doesn't seem to mind old (recent) tokens, so it's no biggie if we race here and a different thread
        # immediately overwrites this. (Dict assigns are atomic.)
        DockerTools.tokens[user+'/'+repo] = r.headers['x-docker-token']
        return DockerTools.tokens[user+'/'+repo], True

    def _registry_request(self, user, repo, tag, token):
        return self.session.get(self.regAPI + "/repositories/{user}/{repo}/tags/{tag}".format(user=user, repo=repo,tag=tag),
                                headers={"Authorization": "Token " + token})

    def verify_image(self, imageid):
        """Verify that the image id is real (user, repo, hash) by looking up its hash in the Docker Registry.
        Said hash is meant to be secret ( see http://bit.ly/1GMChsU ) so we don't return it.
        Raises an exception if the image string is malformed or can't be found."""
        (user, repo, tag) = DockerTools.parse_docker_string(imageid)

        #Docker Registry needs a token, generated from Docker Hub, to get info from private repos.
        token, token_is_fresh = self._get_token(user, repo)
        r = self._registry_request(user, repo, tag, token)

        if r.status_code == 401 and not token_is_fresh:
            # Auth failure, but with an old token. Maybe it's expired?
            token, _ = self._get_token(user, repo, force_new=True)
            r = self._registry_request(user, repo, tag, token)

        if r.status_code == 401:
            # Still 401? We can't recover from this.
            raise HTTPError(400, "Docker is refusing authorization to Herc for {user}/{repo}:{tag}. Maybe it's a private repo?".format(user=user, repo=repo, tag=tag))
        elif r.status_code == 404:
            raise HTTPError(404, "Docker image {user}/{repo} exists, but tag {tag} not found.".format(user=user, repo=repo, tag=tag))
        else:
            r.raise_for_status()  # Bubble up any non-200 statuses.
