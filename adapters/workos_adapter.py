from typing import List, Dict

class WorkOSTaskManager:
    def get_high_priority_client_tasks(self) -> List[Dict]:
        return [
            {
                'client': 'Acme Corp',
                'description': 'Complete Q1 Marketing Dashboard',
                'priority': 'High',
                'due_date': '2026-02-15'
            },
            {
                'client': 'TechStart Inc',
                'description': 'Finalize API Integration Proposal',
                'priority': 'High',
                'due_date': '2026-02-10'
            },
            {
                'client': 'Global Solutions',
                'description': 'Develop Enterprise Security Framework',
                'priority': 'Critical',
                'due_date': '2026-02-05'
            }
        ]