"""
Energy-Aware Task System - Always weights tasks against Oura energy levels.

Integrates Oura readiness with WorkOS and Todoist to recommend tasks
matched to current energy state.
"""

import asyncio
import os
import json
import requests
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class EnergyLevel:
    """Energy state from Oura."""
    readiness_score: int
    sleep_score: int
    activity_score: int
    category: str  # low, moderate, high
    date: str
    
    @property
    def can_handle_complex(self) -> bool:
        """Can user handle complex tasks?"""
        return self.readiness_score >= 70
    
    @property
    def can_handle_moderate(self) -> bool:
        """Can user handle moderate tasks?"""
        return self.readiness_score >= 50
    
    @property
    def should_rest(self) -> bool:
        """Should user prioritize rest?"""
        return self.readiness_score < 50


@dataclass
class Task:
    """Unified task representation."""
    title: str
    source: str  # 'workos' or 'todoist'
    complexity: str  # 'simple', 'moderate', 'complex'
    points: int
    client: Optional[str] = None
    project: Optional[str] = None
    due_date: Optional[str] = None
    task_id: Optional[str] = None
    
    def matches_energy(self, energy: EnergyLevel) -> bool:
        """Does this task match current energy level?"""
        if self.complexity == 'simple':
            return True  # Can always do simple tasks
        elif self.complexity == 'moderate':
            return energy.can_handle_moderate
        else:  # complex
            return energy.can_handle_complex


class EnergyAwareTaskSystem:
    """Main system for energy-aware task recommendations."""
    
    def __init__(self):
        # Load .env if not already loaded
        if not os.getenv('OURA_PERSONAL_ACCESS_TOKEN'):
            env_file = Path('.env')
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.strip() and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        
        self.oura_token = os.getenv('OURA_PERSONAL_ACCESS_TOKEN')
        self._load_complexity_rules()
    
    def _load_complexity_rules(self):
        """Load task complexity classification rules."""
        # These can be learned over time
        self.complexity_keywords = {
            'simple': [
                'email', 'call', 'schedule', 'review', 'check',
                'organize', 'file', 'send', 'respond', 'import', 'find',
                'look for', 'survey', 'convert'
            ],
            'moderate': [
                'write', 'analyze', 'document', 'investigate', 'troubleshoot',
                'coordinate', 'plan', 'research', 'prepare', 'update',
                'migrate', 'move records', 'transfer'
            ],
            'complex': [
                'implement', 'architect', 'design', 'refactor',
                'build', 'develop', 'integrate', 'optimize', 'solve',
                # Epic-specific complex indicators
                'orderset', 'smarttext', 'spec', 'specs', 'build + spec',
                'clindoc build', 'interface build'
            ]
        }
        
        # Epic-specific context clues for complexity boost
        self.epic_complex_indicators = [
            'build', 'spec', 'comms', 'orderset', 'smarttext',
            'organ donor', 'mora', 'clinical build'
        ]
    
    async def get_energy_state(self) -> EnergyLevel:
        """Get current energy state from Oura."""
        if not self.oura_token:
            raise ValueError("OURA_PERSONAL_ACCESS_TOKEN not set")
        
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        
        headers = {"Authorization": f"Bearer {self.oura_token}"}
        
        # Get readiness
        readiness_url = f"https://api.ouraring.com/v2/usercollection/daily_readiness?start_date={yesterday}&end_date={today}"
        readiness_resp = requests.get(readiness_url, headers=headers)
        readiness_data = readiness_resp.json().get('data', [])
        readiness_score = readiness_data[-1]['score'] if readiness_data else 50
        
        # Get sleep
        sleep_url = f"https://api.ouraring.com/v2/usercollection/daily_sleep?start_date={yesterday}&end_date={today}"
        sleep_resp = requests.get(sleep_url, headers=headers)
        sleep_data = sleep_resp.json().get('data', [])
        sleep_score = sleep_data[-1]['score'] if sleep_data else 50
        
        # Get activity
        activity_url = f"https://api.ouraring.com/v2/usercollection/daily_activity?start_date={yesterday}&end_date={today}"
        activity_resp = requests.get(activity_url, headers=headers)
        activity_data = activity_resp.json().get('data', [])
        activity_score = activity_data[-1]['score'] if activity_data else 50
        
        # Categorize
        if readiness_score >= 70:
            category = 'high'
        elif readiness_score >= 50:
            category = 'moderate'
        else:
            category = 'low'
        
        return EnergyLevel(
            readiness_score=readiness_score,
            sleep_score=sleep_score,
            activity_score=activity_score,
            category=category,
            date=today
        )
    
    def classify_task_complexity(self, title: str, points: int = 0) -> str:
        """Classify task complexity based on title and points."""
        title_lower = title.lower()
        
        # Epic-specific: Check for complex build indicators
        epic_complex_count = sum(1 for indicator in self.epic_complex_indicators if indicator in title_lower)
        if epic_complex_count >= 2:  # "build" + "spec" or similar
            return 'complex'
        
        # Check keywords
        matched_complexity = None
        for complexity, keywords in self.complexity_keywords.items():
            if any(kw in title_lower for kw in keywords):
                matched_complexity = complexity
                break
        
        # Apply points modifier if we have a match
        if matched_complexity:
            if points >= 5:
                return 'complex'
            elif points >= 3 and matched_complexity != 'complex':
                return 'moderate'
            return matched_complexity
        
        # Default based on points alone
        if points >= 5:
            return 'complex'
        elif points >= 2:
            return 'moderate'
        return 'simple'
    
    async def get_work_tasks(self) -> List[Task]:
        """Get tasks from WorkOS."""
        from Tools.core.workos_gateway import WorkOSGateway
        
        # Load env from .env file
        env_file = Path('.env')
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        
        gateway = WorkOSGateway()
        work_tasks = await gateway.get_tasks(status="active", limit=50) or []

        tasks = []
        for task in work_tasks:
            title = task.get('title', 'Untitled')

            # Normalize points across MCP/DB shapes
            points = (
                task.get('points')
                or task.get('pointsFinal')
                or task.get('pointsAiGuess')
                or task.get('effortEstimate')
                or task.get('effort_estimate')
                or 0
            )

            complexity = self.classify_task_complexity(title, points)

            client_name = task.get('clientName')
            if not client_name:
                client = task.get('client', {})
                if isinstance(client, dict):
                    client_name = client.get('name')

            tasks.append(Task(
                title=title,
                source='workos',
                complexity=complexity,
                points=points,
                client=client_name,
                task_id=str(task.get('id', ''))
            ))
        
        return tasks
    
    def get_personal_tasks(self) -> List[Task]:
        """Get tasks from Todoist."""
        import subprocess
        
        try:
            result = subprocess.run(
                ['todoist', 'today'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            tasks = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # Format: "ID  Title (today)"
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        task_id, title_with_date = parts
                        title = title_with_date.replace(' (today)', '').strip()
                        complexity = self.classify_task_complexity(title, 1)
                        
                        tasks.append(Task(
                            title=title,
                            source='todoist',
                            complexity=complexity,
                            points=1,
                            task_id=task_id
                        ))
            
            return tasks
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
    
    async def get_recommendations(self) -> Dict[str, Any]:
        """Get energy-aware task recommendations."""
        energy = await self.get_energy_state()
        work_tasks = await self.get_work_tasks()
        personal_tasks = self.get_personal_tasks()
        
        all_tasks = work_tasks + personal_tasks
        
        # Match tasks to energy
        matched = [t for t in all_tasks if t.matches_energy(energy)]
        too_hard = [t for t in all_tasks if not t.matches_energy(energy) and t.complexity != 'simple']
        
        return {
            'energy': asdict(energy),
            'recommendations': {
                'matched_tasks': [asdict(t) for t in matched],
                'too_hard_today': [asdict(t) for t in too_hard],
                'total_available': len(matched),
                'deferred': len(too_hard)
            },
            'guidance': self._generate_guidance(energy, matched, too_hard)
        }
    
    def _generate_guidance(self, energy: EnergyLevel, matched: List[Task], too_hard: List[Task]) -> str:
        """Generate human-readable guidance."""
        if energy.should_rest:
            return (
                f"⚠️  Low energy day (readiness {energy.readiness_score}). "
                f"Focus on {len([t for t in matched if t.complexity == 'simple'])} simple tasks. "
                f"Defer {len(too_hard)} complex tasks. Prioritize recovery."
            )
        elif energy.can_handle_complex:
            complex_count = len([t for t in matched if t.complexity == 'complex'])
            return (
                f"✨ High energy (readiness {energy.readiness_score}). "
                f"Tackle {complex_count} complex tasks while you have the capacity."
            )
        else:
            moderate_count = len([t for t in matched if t.complexity == 'moderate'])
            return (
                f"🔋 Moderate energy (readiness {energy.readiness_score}). "
                f"Handle {moderate_count} moderate tasks. Save complex work for higher energy days."
            )


async def main():
    """CLI interface."""
    system = EnergyAwareTaskSystem()
    recommendations = await system.get_recommendations()
    
    energy = recommendations['energy']
    recs = recommendations['recommendations']
    
    print(f"\n{'='*60}")
    print(f"ENERGY-AWARE TASK RECOMMENDATIONS")
    print(f"{'='*60}")
    print(f"\nEnergy State: {energy['category'].upper()} (Readiness: {energy['readiness_score']})")
    print(f"Sleep: {energy['sleep_score']} | Activity: {energy['activity_score']}")
    print(f"\n{recommendations['guidance']}")
    
    print(f"\n{'─'*60}")
    print(f"MATCHED TO YOUR ENERGY ({recs['total_available']} tasks)")
    print(f"{'─'*60}")
    
    for task in recs['matched_tasks'][:10]:
        source_icon = '💼' if task['source'] == 'workos' else '🏠'
        complexity_icon = {'simple': '●', 'moderate': '●●', 'complex': '●●●'}[task['complexity']]
        client_info = f"[{task['client']}] " if task.get('client') else ""
        print(f"{source_icon} {complexity_icon} {client_info}{task['title']}")
    
    if recs['deferred']:
        print(f"\n{'─'*60}")
        print(f"DEFER UNTIL HIGHER ENERGY ({recs['deferred']} tasks)")
        print(f"{'─'*60}")
        for task in recs['too_hard_today'][:5]:
            source_icon = '💼' if task['source'] == 'workos' else '🏠'
            client_info = f"[{task['client']}] " if task.get('client') else ""
            print(f"{source_icon} ●●● {client_info}{task['title']}")


if __name__ == '__main__':
    asyncio.run(main())
