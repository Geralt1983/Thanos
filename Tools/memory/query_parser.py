"""
Temporal Query Parser for Thanos Memory System.

Parses natural language queries about past activities into
structured query parameters for database and vector search.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import calendar


class QueryType(Enum):
    """Types of memory queries."""
    DAY_RECALL = "day_recall"           # What did I do on X?
    PROJECT_HISTORY = "project_history"  # When did I work on X?
    STRUGGLE_RECALL = "struggle_recall"  # What was I struggling with?
    ACCOMPLISHMENT = "accomplishment"    # What did I accomplish?
    PATTERN_ANALYSIS = "pattern_analysis"  # Show me my X pattern
    ENTITY_QUERY = "entity_query"        # Everything about X
    TIME_COMPARISON = "time_comparison"  # Compare X vs Y
    GENERAL_SEARCH = "general_search"    # Free-form search


@dataclass
class TemporalQuery:
    """Parsed temporal query parameters."""
    query_type: QueryType
    original_query: str

    # Date range
    date_range: Optional[Tuple[date, date]] = None
    specific_date: Optional[date] = None

    # Filters
    project: Optional[str] = None
    entity: Optional[str] = None
    activity_types: Optional[List[str]] = None
    domain: Optional[str] = None

    # Query specifics
    search_terms: Optional[List[str]] = None
    comparison_periods: Optional[List[Tuple[date, date]]] = None

    # Options
    wants_summary: bool = True
    limit: int = 20

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query_type': self.query_type.value,
            'original_query': self.original_query,
            'date_range': (
                (self.date_range[0].isoformat(), self.date_range[1].isoformat())
                if self.date_range else None
            ),
            'specific_date': self.specific_date.isoformat() if self.specific_date else None,
            'project': self.project,
            'entity': self.entity,
            'activity_types': self.activity_types,
            'domain': self.domain,
            'search_terms': self.search_terms,
            'wants_summary': self.wants_summary,
            'limit': self.limit
        }


# Day name to weekday number mapping (Monday = 0)
DAY_NAMES = {
    'monday': 0, 'mon': 0,
    'tuesday': 1, 'tue': 1, 'tues': 1,
    'wednesday': 2, 'wed': 2,
    'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
    'friday': 4, 'fri': 4,
    'saturday': 5, 'sat': 5,
    'sunday': 6, 'sun': 6,
}

# Relative time expressions
RELATIVE_TIME_PATTERNS = {
    r'\byesterday\b': lambda: date.today() - timedelta(days=1),
    r'\btoday\b': lambda: date.today(),
    r'\b(\d+)\s*days?\s*ago\b': lambda m: date.today() - timedelta(days=int(m.group(1))),
    r'\b(\d+)\s*weeks?\s*ago\b': lambda m: date.today() - timedelta(weeks=int(m.group(1))),
}


class TemporalQueryParser:
    """
    Parses natural language queries into structured temporal parameters.

    Supports queries like:
    - "What did I do last Tuesday?"
    - "When did I last work on Memphis?"
    - "What was I struggling with yesterday?"
    - "Show me my productivity pattern this week"
    - "What did I accomplish this month?"
    """

    # Query type detection patterns
    QUERY_PATTERNS = [
        # Day recall
        (r'\bwhat did i do\b', QueryType.DAY_RECALL),
        (r'\bwhat happened\b', QueryType.DAY_RECALL),
        (r'\bshow me .* activities?\b', QueryType.DAY_RECALL),

        # Project history
        (r'\bwhen did i (?:last )?(work on|touch|update)\b', QueryType.PROJECT_HISTORY),
        (r'\blast time i worked on\b', QueryType.PROJECT_HISTORY),
        (r'\bhistory (?:of|for)\b', QueryType.PROJECT_HISTORY),

        # Struggle recall
        (r'\bwhat (?:was|were) i struggling with\b', QueryType.STRUGGLE_RECALL),
        (r'\bstruggl(?:e|ed|ing)\b', QueryType.STRUGGLE_RECALL),
        (r'\bproblems?\b', QueryType.STRUGGLE_RECALL),
        (r'\bblockers?\b', QueryType.STRUGGLE_RECALL),

        # Accomplishment
        (r'\bwhat did i accomplish\b', QueryType.ACCOMPLISHMENT),
        (r'\bwhat did i complete\b', QueryType.ACCOMPLISHMENT),
        (r'\bmy accomplishments?\b', QueryType.ACCOMPLISHMENT),
        (r'\bwhat got done\b', QueryType.ACCOMPLISHMENT),

        # Pattern analysis
        (r'\b(?:show|tell) me my .* pattern\b', QueryType.PATTERN_ANALYSIS),
        (r'\bproductivity (?:pattern|trend|history)\b', QueryType.PATTERN_ANALYSIS),
        (r'\bhow (?:productive|busy) (?:was|am) i\b', QueryType.PATTERN_ANALYSIS),

        # Entity query
        (r'\beverything about\b', QueryType.ENTITY_QUERY),
        (r'\btell me about\b', QueryType.ENTITY_QUERY),
        (r'\bwhat do i know about\b', QueryType.ENTITY_QUERY),

        # Comparison
        (r'\bcompare\b', QueryType.TIME_COMPARISON),
        (r'\bvs\.?\b', QueryType.TIME_COMPARISON),
        (r'\bversus\b', QueryType.TIME_COMPARISON),
    ]

    def parse(self, query: str) -> TemporalQuery:
        """
        Parse a natural language query into structured parameters.

        Args:
            query: The natural language query.

        Returns:
            TemporalQuery with parsed parameters.
        """
        query_lower = query.lower().strip()

        # Detect query type
        query_type = self._detect_query_type(query_lower)

        # Extract date range
        date_range, specific_date = self._extract_dates(query_lower)

        # Extract project/entity references
        project = self._extract_project(query_lower)
        entity = self._extract_entity(query)  # Keep original case for names

        # Extract domain
        domain = self._extract_domain(query_lower)

        # Extract search terms (remaining meaningful words)
        search_terms = self._extract_search_terms(query_lower, project, entity)

        return TemporalQuery(
            query_type=query_type,
            original_query=query,
            date_range=date_range,
            specific_date=specific_date,
            project=project,
            entity=entity,
            domain=domain,
            search_terms=search_terms,
            wants_summary=True,
            limit=20
        )

    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the type of query from the text."""
        for pattern, qtype in self.QUERY_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return qtype

        return QueryType.GENERAL_SEARCH

    def _extract_dates(self, query: str) -> Tuple[Optional[Tuple[date, date]], Optional[date]]:
        """
        Extract date range or specific date from query.

        Returns:
            Tuple of (date_range, specific_date).
            Only one will be set based on the query.
        """
        today = date.today()

        # Check for specific day references
        # "last Tuesday", "this Monday", etc.
        match = re.search(r'\b(last|this|past)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b', query, re.I)
        if match:
            modifier = match.group(1).lower()
            day_name = match.group(2).lower()
            target_day = DAY_NAMES.get(day_name[:3], 0)

            if modifier in ('last', 'past'):
                # Find the most recent occurrence of that day
                days_back = (today.weekday() - target_day) % 7
                if days_back == 0:
                    days_back = 7  # If today is that day, go back a week
                specific = today - timedelta(days=days_back)
            else:  # 'this'
                # Find this week's occurrence
                days_diff = target_day - today.weekday()
                if days_diff < 0:
                    days_diff += 7
                specific = today + timedelta(days=days_diff)

            return None, specific

        # Check for relative time expressions
        for pattern, resolver in RELATIVE_TIME_PATTERNS.items():
            match = re.search(pattern, query, re.I)
            if match:
                if callable(resolver):
                    try:
                        specific = resolver(match) if match.groups() else resolver()
                        return None, specific
                    except Exception:
                        pass

        # Check for week references
        if re.search(r'\bthis week\b', query, re.I):
            start = today - timedelta(days=today.weekday())  # Monday
            end = start + timedelta(days=6)  # Sunday
            return (start, end), None

        if re.search(r'\blast week\b', query, re.I):
            start = today - timedelta(days=today.weekday() + 7)
            end = start + timedelta(days=6)
            return (start, end), None

        # Check for month references
        if re.search(r'\bthis month\b', query, re.I):
            start = today.replace(day=1)
            _, last_day = calendar.monthrange(today.year, today.month)
            end = today.replace(day=last_day)
            return (start, end), None

        if re.search(r'\blast month\b', query, re.I):
            first_of_this_month = today.replace(day=1)
            end = first_of_this_month - timedelta(days=1)
            start = end.replace(day=1)
            return (start, end), None

        # Check for "past N days"
        match = re.search(r'\bpast\s+(\d+)\s*days?\b', query, re.I)
        if match:
            days = int(match.group(1))
            start = today - timedelta(days=days)
            return (start, today), None

        # Default: no date specified
        return None, None

    def _extract_project(self, query: str) -> Optional[str]:
        """Extract project name from query."""
        # Look for patterns like "on <project>", "the <project> project"
        patterns = [
            r'\bon\s+(?:the\s+)?([a-z][a-z0-9_-]+)\s+(?:project|work|task)?\b',
            r'\bwork(?:ing|ed)? on\s+(?:the\s+)?([a-z][a-z0-9_-]+)\b',
            r'\b(?:the\s+)?([a-z][a-z0-9_-]+)\s+project\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.I)
            if match:
                project = match.group(1)
                # Filter out common words
                if project.lower() not in ('the', 'this', 'that', 'my', 'a', 'an'):
                    return project

        return None

    def _extract_entity(self, query: str) -> Optional[str]:
        """Extract person/entity name from query."""
        # Look for capitalized names
        patterns = [
            r'\babout\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            r'\bwith\s+([A-Z][a-z]+)\b',
            r'\bfrom\s+([A-Z][a-z]+)\b',
            r'\b([A-Z][a-z]+)\'s\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                entity = match.group(1)
                # Filter out common words
                common = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                         'Saturday', 'Sunday', 'January', 'February', 'March',
                         'April', 'May', 'June', 'July', 'August', 'September',
                         'October', 'November', 'December', 'Today', 'Yesterday',
                         'This', 'That', 'What', 'When', 'Where', 'How', 'Why'}
                if entity not in common:
                    return entity

        return None

    def _extract_domain(self, query: str) -> Optional[str]:
        """Extract domain (work/personal) from query."""
        if re.search(r'\bwork\b', query, re.I):
            return 'work'
        if re.search(r'\bpersonal\b', query, re.I):
            return 'personal'
        return None

    def _extract_search_terms(
        self,
        query: str,
        project: Optional[str],
        entity: Optional[str]
    ) -> Optional[List[str]]:
        """Extract remaining search terms from query."""
        # Remove common query words
        stop_words = {
            'what', 'did', 'do', 'i', 'me', 'my', 'show', 'tell', 'about',
            'when', 'where', 'how', 'the', 'a', 'an', 'on', 'in', 'at',
            'last', 'this', 'past', 'was', 'were', 'been', 'have', 'has',
            'work', 'working', 'worked', 'with', 'for', 'from', 'to',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday', 'week', 'month', 'day', 'days',
            'yesterday', 'today', 'ago', 'pattern', 'history', 'activity',
            'activities', 'accomplish', 'complete', 'completed'
        }

        words = re.findall(r'\b[a-z]+\b', query.lower())
        terms = [w for w in words if w not in stop_words]

        # Remove project and entity if already extracted
        if project:
            terms = [t for t in terms if t.lower() != project.lower()]
        if entity:
            terms = [t for t in terms if t.lower() != entity.lower()]

        return terms if terms else None

    def get_date_description(self, query: TemporalQuery) -> str:
        """Get a human-readable description of the date range."""
        if query.specific_date:
            if query.specific_date == date.today():
                return "today"
            elif query.specific_date == date.today() - timedelta(days=1):
                return "yesterday"
            else:
                return query.specific_date.strftime("%A, %B %d, %Y")

        if query.date_range:
            start, end = query.date_range
            if start == end:
                return start.strftime("%A, %B %d")

            # Check if it's a week
            if (end - start).days == 6:
                if start == date.today() - timedelta(days=date.today().weekday()):
                    return "this week"
                return f"week of {start.strftime('%B %d')}"

            # Check if it's a month
            if start.day == 1 and end.month == start.month:
                return start.strftime("%B %Y")

            return f"{start.strftime('%b %d')} to {end.strftime('%b %d')}"

        return "all time"


# Convenience function
def parse_query(query: str) -> TemporalQuery:
    """
    Convenience function to parse a temporal query.

    Args:
        query: Natural language query.

    Returns:
        Parsed TemporalQuery.
    """
    parser = TemporalQueryParser()
    return parser.parse(query)


if __name__ == "__main__":
    # Test the parser
    test_queries = [
        "What did I do last Tuesday?",
        "When did I last work on Memphis?",
        "What was I struggling with yesterday?",
        "Show me my productivity pattern this week",
        "What did I accomplish this month?",
        "Tell me about Mike",
        "What happened 3 days ago?",
        "Compare this week vs last week",
        "Show me work activities from last week",
    ]

    parser = TemporalQueryParser()

    for query in test_queries:
        result = parser.parse(query)
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Type: {result.query_type.value}")
        print(f"Date: {parser.get_date_description(result)}")
        if result.project:
            print(f"Project: {result.project}")
        if result.entity:
            print(f"Entity: {result.entity}")
        if result.domain:
            print(f"Domain: {result.domain}")
        if result.search_terms:
            print(f"Search terms: {result.search_terms}")
