"""
图书管理员代理 (Librarian Agent)

负责管理技能库和插件库的知识，提供语义搜索和元数据管理功能。
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not available, using file-based search")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("Sentence transformers not available, using basic search")

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str
    version: str
    description: str
    tags: List[str]
    parameters: Dict[str, Any]
    file_path: str
    source_code_path: Optional[str] = None
    security_policy: Optional[str] = None


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    file_path: str
    source_code_path: Optional[str] = None
    security_policy: Optional[str] = None


@dataclass
class SearchResult:
    """搜索结果"""
    item: Any  # SkillMetadata or PluginMetadata
    confidence: float
    matched_terms: List[str]


class Librarian:
    """图书管理员代理"""
    
    def __init__(self, 
                 skill_library_path: str = "skill_library",
                 plugin_library_path: str = "plugins",
                 vector_db_path: str = "vector_db"):
        """初始化图书管理员"""
        self.skill_library_path = Path(skill_library_path)
        self.plugin_library_path = Path(plugin_library_path)
        self.vector_db_path = Path(vector_db_path)
        
        # 初始化向量数据库
        self._init_vector_db()
        
        # 初始化嵌入模型
        self._init_embedding_model()
        
        # 加载元数据
        self.skills: Dict[str, SkillMetadata] = {}
        self.plugins: Dict[str, PluginMetadata] = {}
        self._load_metadata()
    
    def _init_vector_db(self):
        """初始化向量数据库"""
        self.vector_db = None
        self.skills_collection = None
        self.plugins_collection = None
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not available, using file-based storage")
            return
            
        try:
            self.vector_db = chromadb.PersistentClient(
                path=str(self.vector_db_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 创建集合
            self.skills_collection = self.vector_db.get_or_create_collection("skills")
            self.plugins_collection = self.vector_db.get_or_create_collection("plugins")
            
            logger.info("Vector database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            self.vector_db = None
    
    def _init_embedding_model(self):
        """初始化嵌入模型"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("Sentence transformers not available, using basic search")
            self.embedding_model = None
            return
            
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
    
    def _load_metadata(self):
        """加载技能和插件的元数据"""
        self._load_skills()
        self._load_plugins()
        self._update_vector_db()
    
    def _load_skills(self):
        """加载技能元数据"""
        if not self.skill_library_path.exists():
            logger.warning(f"Skill library path does not exist: {self.skill_library_path}")
            return
            
        for skill_dir in self.skill_library_path.iterdir():
            if skill_dir.is_dir():
                skill_json_path = skill_dir / "skill.json"
                if skill_json_path.exists():
                    try:
                        with open(skill_json_path, 'r', encoding='utf-8') as f:
                            skill_data = json.load(f)
                        
                        skill_metadata = SkillMetadata(
                            name=skill_data.get('skill_name', skill_dir.name),
                            version=skill_data.get('version', '1.0.0'),
                            description=skill_data.get('description', ''),
                            tags=skill_data.get('tags', []),
                            parameters=skill_data.get('parameters', {}),
                            file_path=str(skill_dir),
                            source_code_path=skill_data.get('source_code_path'),
                            security_policy=skill_data.get('security_policy')
                        )
                        
                        self.skills[skill_metadata.name] = skill_metadata
                        logger.debug(f"Loaded skill: {skill_metadata.name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to load skill from {skill_dir}: {e}")
        
        logger.info(f"Loaded {len(self.skills)} skills")
    
    def _load_plugins(self):
        """加载插件元数据"""
        if not self.plugin_library_path.exists():
            logger.warning(f"Plugin library path does not exist: {self.plugin_library_path}")
            return
            
        # 遍历插件目录
        for plugin_file in self.plugin_library_path.rglob("*.json"):
            if plugin_file.name.endswith("_spec.json"):
                try:
                    with open(plugin_file, 'r', encoding='utf-8') as f:
                        plugin_data = json.load(f)
                    
                    plugin_metadata = PluginMetadata(
                        name=plugin_data.get('name', plugin_file.stem),
                        version=plugin_data.get('version', '1.0.0'),
                        description=plugin_data.get('description', ''),
                        author=plugin_data.get('author', 'Unknown'),
                        inputs=plugin_data.get('inputs', []),
                        outputs=plugin_data.get('outputs', []),
                        file_path=str(plugin_file),
                        source_code_path=plugin_data.get('source_code_path'),
                        security_policy=plugin_data.get('security_policy')
                    )
                    
                    self.plugins[plugin_metadata.name] = plugin_metadata
                    logger.debug(f"Loaded plugin: {plugin_metadata.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load plugin from {plugin_file}: {e}")
        
        logger.info(f"Loaded {len(self.plugins)} plugins")
    
    def _update_vector_db(self):
        """更新向量数据库"""
        if not self.vector_db or not self.embedding_model:
            return
            
        try:
            # 更新技能向量
            skill_texts = []
            skill_ids = []
            skill_metadatas = []
            
            for skill in self.skills.values():
                text = f"{skill.name} {skill.description} {' '.join(skill.tags)}"
                skill_texts.append(text)
                skill_ids.append(skill.name)
                skill_metadatas.append({
                    "name": skill.name,
                    "version": skill.version,
                    "description": skill.description,
                    "tags": skill.tags,
                    "parameters": skill.parameters
                })
            
            if skill_texts:
                embeddings = self.embedding_model.encode(skill_texts)
                self.skills_collection.add(
                    embeddings=embeddings.tolist(),
                    ids=skill_ids,
                    metadatas=skill_metadatas
                )
            
            # 更新插件向量
            plugin_texts = []
            plugin_ids = []
            plugin_metadatas = []
            
            for plugin in self.plugins.values():
                text = f"{plugin.name} {plugin.description}"
                plugin_texts.append(text)
                plugin_ids.append(plugin.name)
                plugin_metadatas.append({
                    "name": plugin.name,
                    "version": plugin.version,
                    "description": plugin.description,
                    "author": plugin.author
                })
            
            if plugin_texts:
                embeddings = self.embedding_model.encode(plugin_texts)
                self.plugins_collection.add(
                    embeddings=embeddings.tolist(),
                    ids=plugin_ids,
                    metadatas=plugin_metadatas
                )
                
            logger.info("Vector database updated successfully")
            
        except Exception as e:
            logger.error(f"Failed to update vector database: {e}")
    
    def find_skill(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """查找技能"""
        if self.vector_db and self.embedding_model:
            return self._find_skill_vector(query, top_k)
        else:
            return self._find_skill_basic(query, top_k)
    
    def _find_skill_vector(self, query: str, top_k: int) -> List[SearchResult]:
        """使用向量搜索查找技能"""
        try:
            query_embedding = self.embedding_model.encode([query])
            results = self.skills_collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k
            )
            
            search_results = []
            for i, (id, distance, metadata) in enumerate(zip(
                results['ids'][0], results['distances'][0], results['metadatas'][0]
            )):
                if id in self.skills:
                    confidence = 1.0 - distance  # 距离越小，置信度越高
                    search_results.append(SearchResult(
                        item=self.skills[id],
                        confidence=confidence,
                        matched_terms=[query]
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return self._find_skill_basic(query, top_k)
    
    def _find_skill_basic(self, query: str, top_k: int) -> List[SearchResult]:
        """使用基本搜索查找技能"""
        query_lower = query.lower()
        results = []
        
        for skill in self.skills.values():
            score = 0
            matched_terms = []
            
            # 名称匹配
            if query_lower in skill.name.lower():
                score += 3
                matched_terms.append(skill.name)
            
            # 描述匹配
            if query_lower in skill.description.lower():
                score += 2
                matched_terms.append("description")
            
            # 标签匹配
            for tag in skill.tags:
                if query_lower in tag.lower():
                    score += 1
                    matched_terms.append(tag)
            
            if score > 0:
                confidence = min(score / 5.0, 1.0)  # 归一化到0-1
                results.append(SearchResult(
                    item=skill,
                    confidence=confidence,
                    matched_terms=matched_terms
                ))
        
        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:top_k]
    
    def find_plugin(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """查找插件"""
        if self.vector_db and self.embedding_model:
            return self._find_plugin_vector(query, top_k)
        else:
            return self._find_plugin_basic(query, top_k)
    
    def _find_plugin_vector(self, query: str, top_k: int) -> List[SearchResult]:
        """使用向量搜索查找插件"""
        try:
            query_embedding = self.embedding_model.encode([query])
            results = self.plugins_collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k
            )
            
            search_results = []
            for i, (id, distance, metadata) in enumerate(zip(
                results['ids'][0], results['distances'][0], results['metadatas'][0]
            )):
                if id in self.plugins:
                    confidence = 1.0 - distance
                    search_results.append(SearchResult(
                        item=self.plugins[id],
                        confidence=confidence,
                        matched_terms=[query]
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return self._find_plugin_basic(query, top_k)
    
    def _find_plugin_basic(self, query: str, top_k: int) -> List[SearchResult]:
        """使用基本搜索查找插件"""
        query_lower = query.lower()
        results = []
        
        for plugin in self.plugins.values():
            score = 0
            matched_terms = []
            
            # 名称匹配
            if query_lower in plugin.name.lower():
                score += 3
                matched_terms.append(plugin.name)
            
            # 描述匹配
            if query_lower in plugin.description.lower():
                score += 2
                matched_terms.append("description")
            
            # 作者匹配
            if query_lower in plugin.author.lower():
                score += 1
                matched_terms.append(plugin.author)
            
            if score > 0:
                confidence = min(score / 5.0, 1.0)
                results.append(SearchResult(
                    item=plugin,
                    confidence=confidence,
                    matched_terms=matched_terms
                ))
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:top_k]
    
    def get_source_code_path(self, item_name: str, item_type: str = "skill") -> Optional[str]:
        """获取源码路径，检查安全策略"""
        if item_type == "skill":
            item = self.skills.get(item_name)
        else:
            item = self.plugins.get(item_name)
        
        if not item:
            return None
        
        # 检查安全策略
        if item.security_policy == "restricted":
            logger.warning(f"Access to {item_name} is restricted by security policy")
            return None
        
        return item.source_code_path or item.file_path
    
    def add_skill(self, skill_name: str, skill_data: Dict[str, Any]) -> bool:
        """添加新技能到技能库"""
        try:
            # 创建技能目录
            skill_dir = self.skill_library_path / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            
            # 写入技能元数据
            skill_json_path = skill_dir / "skill.json"
            with open(skill_json_path, 'w', encoding='utf-8') as f:
                json.dump(skill_data, f, indent=2, ensure_ascii=False)
            
            # 写入主代码文件
            main_py_path = skill_dir / "main.py"
            if "code" in skill_data:
                with open(main_py_path, 'w', encoding='utf-8') as f:
                    f.write(skill_data["code"])
            
            # 提交到Git仓库
            self._commit_to_git(skill_dir, f"Add skill: {skill_name}")
            
            # 重新加载元数据
            self._load_metadata()
            
            logger.info(f"Successfully added skill: {skill_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add skill {skill_name}: {e}")
            return False
    
    def _commit_to_git(self, path: Path, message: str):
        """提交到Git仓库"""
        try:
            # 添加文件
            subprocess.run(["git", "add", str(path)], check=True, capture_output=True)
            
            # 提交
            subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True)
            
            # 推送
            subprocess.run(["git", "push"], check=True, capture_output=True)
            
            logger.info(f"Git commit successful: {message}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            raise
