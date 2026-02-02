"""
Unified Memory Capture Interface for Thanos.

Single entry point that intelligently routes content to:
- Memory V2 (vector store) for searchable facts
- Graphiti (knowledge graph) for entities and relationships

Decision Logic (based on HEARTBEAT.md):
- Entities/relationships → Graphiti
- Searchable facts → Memory V2
- Important content → BOTH
- Routine chatter → SKIP

Usage:
    from Tools.memory_v2.unified_capture import capture, CaptureType
    
    # Automatic routing
    capture("Jeremy decided to switch to Voyage embeddings for better performance")
    
    # Explicit routing
    capture("API key stored in .env", capture_type=CaptureType.FACT)
    capture("Jeremy works with Ashley on ScottCare project", capture_type=CaptureType.RELATIONSHIP)
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CaptureType(Enum):
    """Type of content being captured."""
    DECISION = "decision"          # Strategic decisions → Both
    FACT = "fact"                  # Searchable facts → Memory V2
    PATTERN = "pattern"            # Observed patterns → Memory V2
    RELATIONSHIP = "relationship"  # Entity connections → Graphiti
    NOTE = "note"                 # General notes → Memory V2
    LEARNING = "learning"         # Technical learnings → Both
    SKIP = "skip"                 # Don't capture


class UnifiedCapture:
    """
    Unified capture interface for Memory V2 and Graphiti.
    
    Intelligently routes content based on type and importance.
    """
    
    def __init__(self):
        self.memory_v2 = None
        self.graphiti_available = False
        self._init_services()
    
    def _init_services(self):
        """Initialize Memory V2 and check Graphiti availability."""
        try:
            from .service import get_memory_service
            self.memory_v2 = get_memory_service()
            logger.info("Memory V2 initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Memory V2: {e}")
        
        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-s", "-I", "http://localhost:8000/sse"],
                capture_output=True,
                timeout=2
            )
            self.graphiti_available = result.returncode == 0
            if self.graphiti_available:
                logger.info("Graphiti MCP available")
        except Exception as e:
            logger.warning(f"Graphiti not available: {e}")
    
    def capture(
        self,
        content: str,
        capture_type: Optional[CaptureType] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "openclaw"
    ) -> Dict[str, Any]:
        """
        Capture content to appropriate memory systems.
        
        Args:
            content: The content to capture
            capture_type: Type of content (auto-detected if None)
            metadata: Additional metadata (client, project, entities, etc.)
            source: Source of the capture (default: openclaw)
        
        Returns:
            Dict with capture results from each system
        """
        metadata = metadata or {}
        metadata["source"] = source
        
        # Auto-detect type if not provided
        if capture_type is None:
            capture_type = self._detect_type(content, metadata)
        
        if capture_type == CaptureType.SKIP:
            logger.debug(f"Skipping capture: {content[:50]}...")
            return {"skipped": True, "reason": "routine content"}
        
        results = {}
        
        # Determine routing
        route_to_memory = self._should_route_to_memory(capture_type)
        route_to_graphiti = self._should_route_to_graphiti(capture_type)
        
        # Route to Memory V2
        if route_to_memory and self.memory_v2:
            try:
                metadata["memory_type"] = capture_type.value
                metadata["created_at"] = datetime.now().isoformat()
                metadata["access_count"] = 0
                
                mem_result = self.memory_v2.add(content, metadata=metadata)
                results["memory_v2"] = mem_result
                logger.info(f"Captured to Memory V2: {capture_type.value}")
            except Exception as e:
                logger.error(f"Failed to capture to Memory V2: {e}")
                results["memory_v2_error"] = str(e)
        
        # Route to Graphiti
        if route_to_graphiti and self.graphiti_available:
            try:
                graphiti_result = self._capture_to_graphiti(content, metadata)
                results["graphiti"] = graphiti_result
                logger.info(f"Captured to Graphiti: {capture_type.value}")
            except Exception as e:
                logger.error(f"Failed to capture to Graphiti: {e}")
                results["graphiti_error"] = str(e)
        
        return results
    
    def _detect_type(self, content: str, metadata: Dict[str, Any]) -> CaptureType:
        """
        Auto-detect capture type from content and metadata.
        
        Uses keyword matching and metadata hints.
        """
        content_lower = content.lower()
        
        # Decision indicators
        if any(word in content_lower for word in ["decided", "will", "going to", "plan to", "chosen"]):
            return CaptureType.DECISION
        
        # Relationship indicators
        if any(word in content_lower for word in ["works with", "reports to", "manages", "partner"]):
            return CaptureType.RELATIONSHIP
        
        # Pattern indicators
        if any(word in content_lower for word in ["always", "usually", "tends to", "pattern", "habit"]):
            return CaptureType.PATTERN
        
        # Learning indicators
        if any(word in content_lower for word in ["learned", "discovered", "found that", "realized"]):
            return CaptureType.LEARNING
        
        # Skip indicators
        if any(word in content_lower for word in ["hi", "hello", "ok", "thanks", "got it"]):
            return CaptureType.SKIP
        
        # Check metadata hints
        if metadata.get("entities") or metadata.get("client") or metadata.get("project"):
            return CaptureType.RELATIONSHIP
        
        # Default to fact
        return CaptureType.FACT
    
    def _should_route_to_memory(self, capture_type: CaptureType) -> bool:
        """Determine if content should go to Memory V2."""
        return capture_type in [
            CaptureType.DECISION,
            CaptureType.FACT,
            CaptureType.PATTERN,
            CaptureType.NOTE,
            CaptureType.LEARNING
        ]
    
    def _should_route_to_graphiti(self, capture_type: CaptureType) -> bool:
        """Determine if content should go to Graphiti."""
        return capture_type in [
            CaptureType.DECISION,
            CaptureType.RELATIONSHIP,
            CaptureType.LEARNING
        ]
    
    def _capture_to_graphiti(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture to Graphiti knowledge graph via MCP.
        
        Uses mcporter to call add_episode endpoint.
        """
        import subprocess
        import json
        
        # Build episode name from metadata
        name_parts = []
        if metadata.get("client"):
            name_parts.append(metadata["client"])
        if metadata.get("project"):
            name_parts.append(metadata["project"])
        name_parts.append(datetime.now().strftime("%Y-%m-%d"))
        
        episode_name = " - ".join(name_parts) if name_parts else f"Episode {datetime.now():%Y%m%d}"
        
        # Call Graphiti MCP
        cmd = [
            "mcporter", "call",
            "http://localhost:8000/sse.add_episode",
            f"name={episode_name}",
            f"episode_body={content}",
            "source_description=OpenClaw unified capture",
            "--allow-http"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return {"success": True, "name": episode_name}
        else:
            raise RuntimeError(f"Graphiti capture failed: {result.stderr}")
    
    def capture_batch(
        self,
        items: List[Dict[str, Any]],
        source: str = "openclaw"
    ) -> List[Dict[str, Any]]:
        """
        Capture multiple items in batch.
        
        Args:
            items: List of dicts with 'content', optional 'type' and 'metadata'
            source: Source of the captures
        
        Returns:
            List of capture results
        """
        results = []
        for item in items:
            content = item.get("content")
            if not content:
                continue
            
            capture_type = item.get("type")
            if isinstance(capture_type, str):
                try:
                    capture_type = CaptureType[capture_type.upper()]
                except KeyError:
                    capture_type = None
            
            metadata = item.get("metadata", {})
            
            result = self.capture(content, capture_type, metadata, source)
            results.append(result)
        
        return results


# Singleton instance
_unified_capture: Optional[UnifiedCapture] = None


def get_unified_capture() -> UnifiedCapture:
    """Get or create the singleton UnifiedCapture instance."""
    global _unified_capture
    if _unified_capture is None:
        _unified_capture = UnifiedCapture()
    return _unified_capture


# Convenience function
def capture(
    content: str,
    capture_type: Optional[CaptureType] = None,
    metadata: Optional[Dict[str, Any]] = None,
    source: str = "openclaw"
) -> Dict[str, Any]:
    """
    Capture content to appropriate memory systems.
    
    Convenience wrapper around UnifiedCapture.capture().
    """
    uc = get_unified_capture()
    return uc.capture(content, capture_type, metadata, source)


if __name__ == "__main__":
    # Test unified capture
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python unified_capture.py <content>")
        print("\nExample:")
        print('  python unified_capture.py "Jeremy decided to use Voyage embeddings"')
        sys.exit(1)
    
    content = sys.argv[1]
    result = capture(content)
    
    print("Capture Result:")
    print("=" * 40)
    import json
    print(json.dumps(result, indent=2, default=str))
