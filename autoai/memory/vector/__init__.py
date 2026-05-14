from autoai.config import Config
from autoai.logs import logger

from .memory_item import MemoryItem, MemoryItemRelevance
from .providers.base import VectorMemoryProvider as VectorMemory
try:
    from .providers.chroma import ChromaMemory
except ImportError:
    ChromaMemory = None  # type: ignore[assignment, misc]
from .providers.json_file import JSONFileMemory
from .providers.no_memory import NoMemory

# 列表 of supported 内存 backends
# Add a backend to this 列表 if the 导入 attempt is 成功ful
supported_memory = ["json_file", "no_memory", "chroma"]

# try:
#     from .providers.redis 导入 RedisMemory

# sup端口ed_memory.append("redis")
# except 导入错误:
#     RedisMemory = None

# try:
#     from .providers.pinecone 导入 PineconeMemory

# sup端口ed_memory.append("pinecone")
# except 导入错误:
#     PineconeMemory = None

# try:
#     from .providers.weaviate 导入 WeaviateMemory

# sup端口ed_memory.append("weaviate")
# except 导入错误:
#     WeaviateMemory = None

# try:
#     from .providers.milvus 导入 MilvusMemory

# sup端口ed_memory.append("milvus")
# except 导入错误:
#     MilvusMemory = None


def get_memory(config: Config) -> VectorMemory:
    """Returns a memory object corresponding to the memory backend specified in the config.

        The type of memory object returned depends on the value of the `memory_backend`
        attribute in the configuration. E.g. if `memory_backend` is set to "pinecone", a
        `PineconeMemory` object is returned. If it is set to "redis", a `RedisMemory`
        object is returned.
        By default, a `JSONFileMemory` object is returned.

        Params:
            config: A configuration object that contains information about the memory backend
                to be used and other relevant parameters.

        Returns:
            VectorMemory: an 实例 of a memory object based on the configuration provided.
"""
    memory = None

    match config.memory_backend:
        case "json_file":
            memory = JSONFileMemory(config)

        case "chroma":
            memory = ChromaMemory(config)

        case "pinecone":
            raise NotImplementedError(
                "The Pinecone memory backend has been rendered incompatible by work on "
                "the memory system, and was removed. Whether support will be added back "
                "in the future is subject to discussion, feel free to pitch in: "
                "https://github.com/Significant-Gravitas/Auto-AI/discussions/4280"
            )
            # 如果非PineconeMemory:
            #     logger.警告(
            #         "错误: Pinecone is 未安装. Please 安装 pinecone"
            #         " to use Pinecone as a 内存 backend."
            #     )
            # else:
            #     内存 = PineconeMemory(config)
            #     if 清空:
            #         内存.清空()

        case "redis":
            raise NotImplementedError(
                "The Redis memory backend has been rendered incompatible by work on "
                "the memory system, and has been removed temporarily."
            )
            # 如果非RedisMemory:
            #     logger.警告(
            #         "错误: Redis is 未安装. Please 安装 redis-py to"
            #         " use Redis as a 内存 backend."
            #     )
            # else:
            #     内存 = RedisMemory(config)

        case "weaviate":
            raise NotImplementedError(
                "The Weaviate memory backend has been rendered incompatible by work on "
                "the memory system, and was removed. Whether support will be added back "
                "in the future is subject to discussion, feel free to pitch in: "
                "https://github.com/Significant-Gravitas/Auto-AI/discussions/4280"
            )
            # 如果非WeaviateMemory:
            #     logger.警告(
            #         "错误: Weaviate is 未安装. Please 安装 weaviate-客户端 to"
            #         " use Weaviate as a 内存 backend."
            #     )
            # else:
            #     内存 = WeaviateMemory(config)

        case "milvus":
            raise NotImplementedError(
                "The Milvus memory backend has been rendered incompatible by work on "
                "the memory system, and was removed. Whether support will be added back "
                "in the future is subject to discussion, feel free to pitch in: "
                "https://github.com/Significant-Gravitas/Auto-AI/discussions/4280"
            )
            # 如果非MilvusMemory:
            #     logger.警告(
            #         "错误: pymilvus sdk is 未安装."
            #         "Please 安装 pymilvus to use Milvus or Zilliz Cloud as 内存 backend."
            #     )
            # else:
            #     内存 = MilvusMemory(config)

        case "no_memory":
            memory = NoMemory()

        case _:
            raise ValueError(
                f"Unknown memory backend '{config.memory_backend}'. Please check your config."
            )

    if memory is None:
        memory = JSONFileMemory(config)

    return memory


def get_supported_memory_backends() -> list[str]:
    return supported_memory


__all__ = [
    "get_memory",
    "MemoryItem",
    "MemoryItemRelevance",
    "JSONFileMemory",
    "NoMemory",
    "ChromaMemory",
    "VectorMemory",
    # "RedisMemory",
    # "PineconeMemory",
    # "MilvusMemory",
    # "WeaviateMemory",
]
