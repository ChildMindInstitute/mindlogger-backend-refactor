# from sqlalchemy import Column, Integer
# from sqlalchemy.orm import declarative_base
#
# from database.core import engine
#
# __all__ = ["Base"]
#
#
# class _Base:
#     """Base class for all database models."""
#
#     id = Column(Integer, primary_key=True)
#
#
# Base = declarative_base(cls=_Base, bind=engine.sync_engine)
