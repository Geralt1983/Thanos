#!/usr/bin/env python3
# LEGACY: Transcript-based escalator retained for historical use.
# Canonical escalation logic lives in Tools/model_escalator_v2.py.
import os
import json
import time
import glob
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/Users/jeremy/Projects/Thanos/model_escalator.log'
)
logger = logging.getLogger(__name__)

class ModelEscalator:
    def __init__(self, 
                 transcript_dir: str = '/Users/jeremy/Projects/Thanos/memory/transcripts',
                 processed_dir: str = '/Users/jeremy/Projects/Thanos/memory/processed_transcripts'):
        """
        Initialize ModelEscalator to monitor transcripts and trigger model escalation
        
        :param transcript_dir: Directory to watch for new transcript files
        :param processed_dir: Directory to move processed transcript files
        """
        self.transcript_dir = transcript_dir
        self.processed_dir = processed_dir
        
        # Create directories if they don't exist
        os.makedirs(transcript_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
    
    def analyze_message_complexity(self, message: Dict[Any, Any]) -> float:
        """
        Analyze the complexity of a message
        
        :param message: Message dictionary from transcript
        :return: Complexity score (0.0 - 1.0)
        """
        # Basic complexity heuristics
        complexity = 0.0
        
        # Check message length
        if 'text' in message:
            text = message['text']
            complexity += min(len(text) / 500, 0.3)  # Longer messages more complex
        
        # Check for technical or specialized language
        technical_keywords = [
            'architecture', 'algorithm', 'implementation', 
            'framework', 'design pattern', 'complexity analysis'
        ]
        if any(keyword in message.get('text', '').lower() for keyword in technical_keywords):
            complexity += 0.3
        
        # Check for code or structured content
        if any(marker in message.get('text', '') for marker in ['```', 'def ', 'class ', 'import ']):
            complexity += 0.4
        
        return min(complexity, 1.0)
    
    def should_escalate_model(self, complexity: float) -> bool:
        """
        Determine if model should be escalated based on complexity
        
        :param complexity: Complexity score
        :return: Boolean indicating whether to escalate
        """
        return complexity > 0.5  # Escalate if complexity is over 50%
    
    def process_transcripts(self):
        """
        Monitor and process transcript files for model escalation
        """
        # Find all unprocessed transcript files
        transcript_files = sorted(glob.glob(os.path.join(self.transcript_dir, '*.jsonl')))
        
        for transcript_path in transcript_files:
            try:
                with open(transcript_path, 'r') as f:
                    # Read transcript file line by line
                    for line in f:
                        try:
                            message = json.loads(line)
                            
                            # Analyze message complexity
                            complexity = self.analyze_message_complexity(message)
                            
                            # Check if escalation is needed
                            if self.should_escalate_model(complexity):
                                logger.info(f"Model escalation triggered. Complexity: {complexity}")
                                self.trigger_model_escalation(complexity)
                        
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in line: {line}")
                
                # Move processed file to processed directory
                processed_filename = os.path.basename(transcript_path)
                os.rename(
                    transcript_path, 
                    os.path.join(self.processed_dir, processed_filename)
                )
            
            except Exception as e:
                logger.error(f"Error processing {transcript_path}: {e}")
    
    def trigger_model_escalation(self, complexity: float):
        """
        Call OpenClaw's session_status to escalate model
        
        :param complexity: Complexity score that triggered escalation
        """
        # Placeholder for actual session_status call
        escalation_command = (
            f"openclaw session_status "
            f"--escalate --complexity {complexity}"
        )
        
        try:
            os.system(escalation_command)
            logger.info(f"Escalation triggered with complexity {complexity}")
        except Exception as e:
            logger.error(f"Failed to trigger escalation: {e}")

def main():
    """
    Main function to run the ModelEscalator
    """
    escalator = ModelEscalator()
    
    while True:
        escalator.process_transcripts()
        time.sleep(10)  # Check every 10 seconds

if __name__ == "__main__":
    main()
