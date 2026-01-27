"""
Code Chunking

Intelligent chunking strategies for code and documents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    AST_BASED = "ast_based"
    HYBRID = "hybrid"


@dataclass
class Chunk:
    """A chunk of content."""
    content: str
    start_line: int
    end_line: int
    start_char: int
    end_char: int
    chunk_type: str = "text"  # text, function, class, import, comment
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For code chunks
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    parent_symbol: Optional[str] = None
    
    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1
    
    @property
    def char_count(self) -> int:
        return len(self.content)


@dataclass
class ChunkingConfig:
    """Configuration for chunking."""
    # Size limits
    max_chunk_size: int = 1500  # characters
    min_chunk_size: int = 100
    chunk_overlap: int = 100
    
    # Code-specific
    include_imports: bool = True
    include_docstrings: bool = True
    preserve_functions: bool = True
    preserve_classes: bool = True
    
    # Context
    include_context_lines: int = 2


class Chunker(ABC):
    """Abstract chunker interface."""
    
    @abstractmethod
    def chunk(
        self,
        content: str,
        config: ChunkingConfig,
        language: Optional[str] = None,
    ) -> List[Chunk]:
        pass


class FixedSizeChunker(Chunker):
    """Fixed-size chunking with overlap."""
    
    def chunk(
        self,
        content: str,
        config: ChunkingConfig,
        language: Optional[str] = None,
    ) -> List[Chunk]:
        chunks: List[Chunk] = []
        lines = content.split("\n")
        
        current_chunk_lines: List[str] = []
        current_start_line = 0
        current_char_pos = 0
        chunk_start_char = 0
        
        for i, line in enumerate(lines):
            current_chunk_lines.append(line)
            current_char_pos += len(line) + 1  # +1 for newline
            
            chunk_content = "\n".join(current_chunk_lines)
            
            if len(chunk_content) >= config.max_chunk_size:
                # Create chunk
                chunks.append(Chunk(
                    content=chunk_content,
                    start_line=current_start_line + 1,
                    end_line=i + 1,
                    start_char=chunk_start_char,
                    end_char=current_char_pos,
                    chunk_type="text",
                ))
                
                # Calculate overlap
                overlap_lines = config.chunk_overlap // 50  # Rough estimate
                if overlap_lines > 0 and len(current_chunk_lines) > overlap_lines:
                    current_chunk_lines = current_chunk_lines[-overlap_lines:]
                    current_start_line = i - overlap_lines + 1
                else:
                    current_chunk_lines = []
                    current_start_line = i + 1
                
                chunk_start_char = current_char_pos
        
        # Final chunk
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            if len(chunk_content) >= config.min_chunk_size:
                chunks.append(Chunk(
                    content=chunk_content,
                    start_line=current_start_line + 1,
                    end_line=len(lines),
                    start_char=chunk_start_char,
                    end_char=len(content),
                    chunk_type="text",
                ))
        
        return chunks


class CodeChunker(Chunker):
    """
    Code-aware chunking using language patterns.
    
    Preserves:
    - Function boundaries
    - Class definitions
    - Import blocks
    - Logical code sections
    """
    
    # Language-specific patterns
    PATTERNS = {
        "python": {
            "function": r"^(async\s+)?def\s+(\w+)\s*\(",
            "class": r"^class\s+(\w+)",
            "import": r"^(import|from)\s+",
            "decorator": r"^@\w+",
        },
        "javascript": {
            "function": r"^(async\s+)?function\s+(\w+)|^(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\(",
            "class": r"^class\s+(\w+)",
            "import": r"^import\s+|^const\s+.*=\s*require\(",
            "export": r"^export\s+",
        },
        "typescript": {
            "function": r"^(async\s+)?function\s+(\w+)|^(const|let|var)\s+(\w+)\s*[:<]",
            "class": r"^class\s+(\w+)",
            "interface": r"^interface\s+(\w+)",
            "import": r"^import\s+",
            "export": r"^export\s+",
        },
        "go": {
            "function": r"^func\s+(\w+|\(\w+\s+\*?\w+\))",
            "struct": r"^type\s+(\w+)\s+struct",
            "interface": r"^type\s+(\w+)\s+interface",
            "import": r"^import\s+",
        },
        "rust": {
            "function": r"^(pub\s+)?(async\s+)?fn\s+(\w+)",
            "struct": r"^(pub\s+)?struct\s+(\w+)",
            "impl": r"^impl\s+",
            "use": r"^use\s+",
        },
        "java": {
            "method": r"^(public|private|protected)?\s*(static\s+)?\w+\s+(\w+)\s*\(",
            "class": r"^(public\s+)?class\s+(\w+)",
            "import": r"^import\s+",
        },
    }
    
    def chunk(
        self,
        content: str,
        config: ChunkingConfig,
        language: Optional[str] = None,
    ) -> List[Chunk]:
        if not language or language not in self.PATTERNS:
            # Fall back to fixed-size chunking
            return FixedSizeChunker().chunk(content, config, language)
        
        lines = content.split("\n")
        patterns = self.PATTERNS[language]
        
        # First pass: identify structure
        structure = self._identify_structure(lines, patterns)
        
        # Second pass: create chunks
        chunks = self._create_chunks(lines, structure, config)
        
        return chunks
    
    def _identify_structure(
        self,
        lines: List[str],
        patterns: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Identify code structure (functions, classes, etc.)."""
        structure: List[Dict[str, Any]] = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            for pattern_name, pattern in patterns.items():
                if re.match(pattern, stripped):
                    match = re.match(pattern, stripped)
                    name = None
                    if match and match.groups():
                        # Get the first non-None group as the name
                        for group in match.groups():
                            if group and not group in ["async", "const", "let", "var", "pub"]:
                                name = group
                                break
                    
                    structure.append({
                        "type": pattern_name,
                        "line": i,
                        "name": name,
                        "indent": len(line) - len(line.lstrip()),
                    })
                    break
        
        return structure
    
    def _create_chunks(
        self,
        lines: List[str],
        structure: List[Dict[str, Any]],
        config: ChunkingConfig,
    ) -> List[Chunk]:
        """Create chunks based on identified structure."""
        chunks: List[Chunk] = []
        
        if not structure:
            # No structure found, use fixed-size
            return FixedSizeChunker().chunk("\n".join(lines), config)
        
        # Find boundaries for each structural element
        boundaries: List[Tuple[int, int, Dict[str, Any]]] = []
        
        for i, element in enumerate(structure):
            start_line = element["line"]
            
            # Find end line
            end_line = len(lines) - 1
            for j in range(i + 1, len(structure)):
                next_elem = structure[j]
                if next_elem["indent"] <= element["indent"]:
                    end_line = next_elem["line"] - 1
                    break
            
            # Extend to include trailing blank lines
            while end_line > start_line and not lines[end_line].strip():
                end_line -= 1
            
            boundaries.append((start_line, end_line, element))
        
        # Create chunks from boundaries
        for start, end, element in boundaries:
            chunk_lines = lines[start:end + 1]
            content = "\n".join(chunk_lines)
            
            # Check size limits
            if len(content) > config.max_chunk_size:
                # Split large chunks
                sub_chunks = FixedSizeChunker().chunk(
                    content,
                    config,
                )
                for sub in sub_chunks:
                    sub.start_line += start
                    sub.end_line += start
                    sub.chunk_type = element["type"]
                    sub.symbol_name = element.get("name")
                    chunks.append(sub)
            elif len(content) >= config.min_chunk_size:
                chunks.append(Chunk(
                    content=content,
                    start_line=start + 1,
                    end_line=end + 1,
                    start_char=sum(len(l) + 1 for l in lines[:start]),
                    end_char=sum(len(l) + 1 for l in lines[:end + 1]),
                    chunk_type=element["type"],
                    symbol_name=element.get("name"),
                    symbol_type=element["type"],
                ))
        
        return chunks


class SemanticChunker(Chunker):
    """
    Semantic chunking using sentence embeddings.
    
    Splits content at semantic boundaries (topic changes).
    """
    
    def __init__(self, embeddings_service=None):
        self.embeddings = embeddings_service
    
    def chunk(
        self,
        content: str,
        config: ChunkingConfig,
        language: Optional[str] = None,
    ) -> List[Chunk]:
        # Split into sentences/paragraphs
        paragraphs = self._split_into_paragraphs(content)
        
        if not self.embeddings or len(paragraphs) < 3:
            # Fall back to fixed-size
            return FixedSizeChunker().chunk(content, config, language)
        
        # This would compute embeddings and find semantic boundaries
        # For now, fall back to paragraph-based chunking
        chunks: List[Chunk] = []
        current_chunk: List[str] = []
        current_size = 0
        start_line = 0
        
        for para in paragraphs:
            if current_size + len(para) > config.max_chunk_size and current_chunk:
                chunks.append(Chunk(
                    content="\n\n".join(current_chunk),
                    start_line=start_line + 1,
                    end_line=start_line + sum(p.count("\n") + 1 for p in current_chunk),
                    start_char=0,
                    end_char=sum(len(p) for p in current_chunk),
                    chunk_type="paragraph",
                ))
                current_chunk = []
                current_size = 0
                start_line = chunks[-1].end_line
            
            current_chunk.append(para)
            current_size += len(para)
        
        if current_chunk:
            chunks.append(Chunk(
                content="\n\n".join(current_chunk),
                start_line=start_line + 1,
                end_line=start_line + sum(p.count("\n") + 1 for p in current_chunk),
                start_char=0,
                end_char=sum(len(p) for p in current_chunk),
                chunk_type="paragraph",
            ))
        
        return chunks
    
    def _split_into_paragraphs(self, content: str) -> List[str]:
        """Split content into paragraphs."""
        return [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]


def get_chunker(strategy: ChunkingStrategy, **kwargs) -> Chunker:
    """Factory function to get a chunker by strategy."""
    if strategy == ChunkingStrategy.FIXED_SIZE:
        return FixedSizeChunker()
    elif strategy == ChunkingStrategy.AST_BASED:
        return CodeChunker()
    elif strategy == ChunkingStrategy.SEMANTIC:
        return SemanticChunker(**kwargs)
    elif strategy == ChunkingStrategy.HYBRID:
        return CodeChunker()  # CodeChunker with fallback is effectively hybrid
    else:
        return FixedSizeChunker()
