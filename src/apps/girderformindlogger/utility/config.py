# -*- coding: utf-8 -*-
import os

import cherrypy


def loadConfig():
    cherrypy.config["global"] = {
        "server.socket_host": "127.0.0.1",
        "server.socket_port": 8080,
        "server.thread_pool": 100,
        "server.max_request_body_size": 209715200,
    }
    cherrypy.config["database"] = {
        "uri": f"mongodb://{os.getenv('MONGO__HOST')}:{int(os.getenv('MONGO__PORT'))}/{os.getenv('MONGO__DB')}",
        # "uri": f"mongodb+srv://{os.getenv('MONGO__USER')}:{os.getenv('MONGO__PASSWORD')}@{os.getenv('MONGO__HOST')}/{os.getenv('MONGO__DB')}",
        "replica_set": None,
    }
    cherrypy.config["server"] = {
        "mode": "development",
        "api_root": "api/v1",
        "static_public_path": "/static",
        "disable_event_daemon": False,
    }
    cherrypy.config["logging"] = {}
    cherrypy.config["users"] = {
        "password_regex": ".{6}.*",
        "password_description": "Password must be at least 6 characters.",
    }
    cherrypy.config["cache"] = {
        "enabled": False,
        "cache.global.backend": "dogpile.cache.memory",
        "cache.request.backend": "cherrypy_request",
    }
    cherrypy.config["sentry"] = {
        "backend_dsn": "https://f63bc109e2ea4e618e036a9a0eb6dece@o414302.ingest.sentry.io/5313180",
    }

    # _loadConfigsByPrecedent()

    if "GIRDER_PORT" in os.environ:
        port = int(os.environ["GIRDER_PORT"])
        cherrypy.config["server.socket_port"] = port

    if "database" not in cherrypy.config:
        cherrypy.config["database"] = {}

    if "GIRDER_MONGO_URI" in os.environ:
        cherrypy.config["database"]["uri"] = os.getenv("GIRDER_MONGO_URI")

    if "GIRDER_TEST_DB" in os.environ:
        cherrypy.config["database"]["uri"] = os.environ[
            "GIRDER_TEST_DB"
        ].replace(".", "_")

    if "AES_KEY" in os.environ:
        cherrypy.config["aes_key"] = bytes(os.getenv("AES_KEY"), "utf8")

    cherrypy.config["redis"] = {
        "host": "localhost",
        "port": 6379,
        "password": "",
    }

    redisConf = {
        "host": "REDIS_URI",
        "port": "REDIS_PORT",
        "password": "REDIS_PASSWORD",
    }
    for key in redisConf.keys():
        if redisConf[key] in os.environ:
            cherrypy.config["redis"].update({key: os.getenv(redisConf[key])})


def getConfig():
    if "database" not in cherrypy.config:
        loadConfig()
    # When in Sphinx, cherrypy may be mocked and returning None\
    return cherrypy.config or {}


def getServerMode():
    return getConfig()["server"]["mode"]
