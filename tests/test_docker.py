from unittest import TestCase
from herc.docker import DockerTools
from tornado.web import HTTPError


class TestDocker(TestCase):
    maxDiff = None
    def test_parse_good_docker_strings(self):
        """Test that we correctly parse good docker strings."""
        self.assertEqual( DockerTools.parse_docker_string("foo/bar:baz"), ("foo", "bar", "baz") )
        self.assertEqual( DockerTools.parse_docker_string("foo/bar"), ("foo", "bar", "latest") )
        self.assertEqual( DockerTools.parse_docker_string("bar:baz"), ("library", "bar", "baz") )
        self.assertEqual( DockerTools.parse_docker_string("bar"), ("library", "bar", "latest") )

    def test_parse_bad_docker_strings(self):
        """Test that we correctly except on malformed docker strings."""
        with self.assertRaises(HTTPError):
            DockerTools.parse_docker_string("foo/bar/baz")
        with self.assertRaises(HTTPError):
            DockerTools.parse_docker_string("foo:bar:baz")
