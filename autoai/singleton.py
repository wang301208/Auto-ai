"""确保类只有一个实例的单例元类."""
import abc


class Singleton(abc.ABCMeta, type):
    """
    Singleton metaclass for ensuring only one 实例 of a 类.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """调用 方法 for the singleton metaclass."""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class AbstractSingleton(abc.ABC, metaclass=Singleton):
    """
    Abstract singleton 类 for ensuring only one 实例 of a 类.
    """
