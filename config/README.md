# Calendar Filters Configuration

This directory contains configuration files for customizing how Thanos interacts with your calendar events.

## Quick Start

1. Copy the example file to create your configuration:
   ```bash
   cp config/calendar_filters.json.example config/calendar_filters.json
   ```

2. Edit `config/calendar_filters.json` to customize your filter preferences

3. Restart Thanos or reload the configuration for changes to take effect

## Configuration Overview

The `calendar_filters.json` file controls which calendar events appear in your Thanos context, daily briefings, conflict detection, and time-blocking features.

### Filter Mode

```json
"filter_mode": "exclude"
```

- **exclude**: By default, include all events except those matching exclusion rules
- **include**: By default, exclude all events except those matching inclusion rules

### Main Filter Sections

## 1. Calendar Filters

Filter events by which calendar they come from:

```json
"calendars": {
  "include": ["work@company.com", "primary"],
  "exclude": ["spam-calendar@example.com"],
  "primary_only": false
}
```

**Use cases:**
- Show only events from your work calendar: Set `"primary_only": true` and ensure work is primary
- Exclude a specific shared calendar: Add calendar ID to `"exclude"`
- Combine multiple personal calendars: Add all calendar IDs to `"include"`

## 2. Event Type Filters

Control which types of events are included:

```json
"event_types": {
  "include_all_day_events": true,
  "include_declined_events": false,
  "include_cancelled_events": false,
  "include_tentative_events": true
}
```

**Recommended settings:**
- **Production/work mode**: Set `include_tentative_events: false` to focus on confirmed commitments
- **Planning mode**: Keep `include_tentative_events: true` to see potential conflicts
- **Clean briefings**: Always set `include_declined_events: false` and `include_cancelled_events: false`

## 3. Summary Pattern Filters

Use regex patterns to filter events by their title:

```json
"summary_patterns": {
  "exclude": [
    "^\\[Blocked\\]",           // Exclude events starting with [Blocked]
    "^\\[Hold\\]",              // Exclude events starting with [Hold]
    "(?i)personal.*time",       // Exclude "Personal Time" (case insensitive)
    "(?i)lunch.*break"          // Exclude lunch breaks
  ],
  "include": [],
  "case_sensitive": false
}
```

### Regex Syntax Guide

- `^` - Start of string: `^Meeting` matches "Meeting Notes" but not "Team Meeting"
- `$` - End of string: `Meeting$` matches "Team Meeting" but not "Meeting Notes"
- `.*` - Zero or more of any character: `Team.*Meeting` matches "Team Sync Meeting"
- `(?i)` - Case insensitive: `(?i)standup` matches "Standup", "STANDUP", "StandUp"
- `|` - OR operator: `(?i)lunch|dinner` matches either "Lunch" or "Dinner"
- `[]` - Character class: `[Pp]ersonal` matches "Personal" or "personal"
- `\\[` - Escape special chars: `\\[WIP\\]` matches literal "[WIP]"

### Common Pattern Examples

```json
// Exclude personal events
"exclude": ["(?i)personal", "(?i)family", "(?i)dentist", "(?i)doctor"]

// Exclude time blocks you manage manually
"exclude": ["^\\[Focus\\]", "^\\[Deep Work\\]", "^\\[Buffer\\]"]

// Include only specific meeting types
"include": ["(?i)standup", "(?i)1:1", "(?i)sprint", "(?i)retro"]

// Exclude placeholder/hold events
"exclude": ["^\\[HOLD\\]", "^TBD", "^Placeholder"]
```

## 4. Attendee Filters

Filter based on who's invited to events:

```json
"attendees": {
  "exclude_emails": ["spammy-bot@company.com"],
  "include_emails": ["boss@company.com"],
  "exclude_if_organizer": ["automated-scheduler@company.com"],
  "min_attendees": 2,
  "max_attendees": 10
}
```

**Use cases:**
- **Solo work time**: Set `"max_attendees": 1` to show only your personal time blocks
- **Meetings only**: Set `"min_attendees": 2` to exclude solo work
- **Skip automated events**: Add bot emails to `"exclude_if_organizer"`
- **Important meetings only**: Add key stakeholder emails to `"include_emails"`

## 5. Time Filters

Filter events by when they occur:

```json
"time_filters": {
  "exclude_before_hour": 8,      // Skip events before 8 AM
  "exclude_after_hour": 18,      // Skip events after 6 PM
  "min_duration_minutes": 15,    // Skip events shorter than 15 min
  "max_duration_minutes": 240,   // Skip events longer than 4 hours
  "exclude_weekends": true       // Skip Saturday/Sunday events
}
```

**Use cases:**
- **Work hours only**: Set `exclude_before_hour: 8` and `exclude_after_hour: 18`
- **Filter noise**: Set `min_duration_minutes: 15` to skip 5-min calendar holds
- **Focus on meetings**: Set `min_duration_minutes: 30` to skip short check-ins
- **Work-life balance**: Set `exclude_weekends: true`

## 6. Metadata Filters

Filter by event properties:

```json
"metadata_filters": {
  "exclude_by_color": [11],        // Color IDs from Google Calendar
  "include_by_color": [1, 2, 3],
  "exclude_recurring": false,
  "exclude_private": false,
  "thanos_created_only": false
}
```

**Google Calendar color IDs:**
- 1: Lavender, 2: Sage, 3: Grape, 4: Flamingo, 5: Banana
- 6: Tangerine, 7: Peacock, 8: Graphite, 9: Blueberry, 10: Basil, 11: Tomato

**Use cases:**
- **Color-coded workflow**: Use `include_by_color` to show only specific event types
- **Hide recurring noise**: Set `exclude_recurring: true` to focus on unique events
- **Thanos-only**: Set `thanos_created_only: true` to see only time blocks you created

## 7. Location Filters

Filter by event location:

```json
"location_filters": {
  "exclude_locations": ["Conference Room A"],
  "include_locations": ["Home Office", "Remote"],
  "exclude_virtual_only": false,
  "exclude_in_person_only": false
}
```

**Use cases:**
- **Remote work**: Set `exclude_in_person_only: true` when working from home
- **Office days**: Set `exclude_virtual_only: true` to focus on in-person meetings
- **Specific venues**: Use `include_locations` for events at particular places

## 8. Advanced Settings

Control how filters are applied across Thanos features:

```json
"advanced": {
  "apply_filters_to_briefing": true,
  "apply_filters_to_conflict_detection": false,
  "apply_filters_to_free_slots": true,
  "cache_filtered_results": true,
  "cache_ttl_minutes": 15
}
```

**Important distinctions:**

- **apply_filters_to_briefing**: Should filtered events appear in your daily briefing?
  - `true` = Show only filtered events in briefings (cleaner view)
  - `false` = Show all events in briefings (complete picture)

- **apply_filters_to_conflict_detection**: Should filtered events block scheduling?
  - `true` = Filtered-out events won't cause conflicts (dangerous!)
  - `false` = All events still block time (recommended for safety)

- **apply_filters_to_free_slots**: Should filtered events count as busy time?
  - `true` = Filtered events don't block free slot finding
  - `false` = Filtered events still mark time as busy

**Recommended configuration:**
```json
{
  "apply_filters_to_briefing": true,        // Clean briefings
  "apply_filters_to_conflict_detection": false,  // Safe scheduling
  "apply_filters_to_free_slots": true       // More slots available
}
```

## Preset Configurations

The file includes common preset configurations you can use as templates:

### work_only
Shows only work-related events during business hours
- Excludes personal, family, and lunch events
- Only shows events between 8 AM - 6 PM
- Excludes weekends

### focus_sessions
Shows only focus time and deep work blocks
- Includes events with "focus", "deep work", "coding time" in title
- Shows only solo events (max 1 attendee)

### meetings_only
Shows only meetings with other people
- Requires at least 2 attendees
- Excludes focus time and out-of-office events

**To use a preset**: Copy its configuration into the main filter sections

## Common Configuration Examples

### Example 1: Work-Life Separation
```json
{
  "enabled": true,
  "summary_patterns": {
    "exclude": ["(?i)personal", "(?i)family", "(?i)gym", "(?i)dentist"]
  },
  "time_filters": {
    "exclude_before_hour": 8,
    "exclude_after_hour": 18,
    "exclude_weekends": true
  }
}
```

### Example 2: Deep Work Focus
```json
{
  "enabled": true,
  "summary_patterns": {
    "include": ["(?i)focus", "(?i)deep work", "(?i)coding", "(?i)writing"]
  },
  "attendees": {
    "max_attendees": 1
  },
  "time_filters": {
    "min_duration_minutes": 60
  }
}
```

### Example 3: Meeting-Heavy Role
```json
{
  "enabled": true,
  "attendees": {
    "min_attendees": 2
  },
  "event_types": {
    "include_tentative_events": true
  },
  "summary_patterns": {
    "exclude": ["(?i)hold", "(?i)blocked", "(?i)tentative"]
  }
}
```

### Example 4: Minimal Filtering (See Everything)
```json
{
  "enabled": false
}
```

## Troubleshooting

### Events not appearing in briefings
1. Check if `"enabled": true` at the top level
2. Verify `"apply_filters_to_briefing": true` in advanced settings
3. Check if events match any exclusion patterns
4. Try temporarily setting `"enabled": false` to see all events

### Too many events showing
1. Review your exclusion patterns in `summary_patterns`
2. Set time filters to limit to work hours
3. Use attendee filters to exclude automated events
4. Consider using `"primary_only": true` if you have many calendars

### Filters not taking effect
1. Ensure the config file is valid JSON (use a JSON validator)
2. Check file is named exactly `calendar_filters.json`
3. Restart Thanos or reload configuration
4. Check cache: set `"cache_ttl_minutes": 0` to disable caching temporarily

### Regex patterns not matching
1. Test patterns at https://regex101.com/
2. Remember to use `(?i)` for case-insensitive matching
3. Escape special characters: `\\[`, `\\]`, `\\.`
4. Use `.*` for wildcards, not `*`

## Testing Your Filters

After configuring filters, test them:

```bash
# Check what events are visible with current filters
thanos calendar get_today_events

# List all calendars to find IDs for filtering
thanos calendar list_calendars

# Test conflict detection with filters
thanos calendar check_conflicts --start "2024-01-15T14:00:00" --end "2024-01-15T15:00:00"
```

## Best Practices

1. **Start simple**: Begin with minimal filtering and add rules as needed
2. **Test incrementally**: Add one filter rule at a time and verify results
3. **Use comments**: While JSON doesn't support comments, use descriptive preset names
4. **Version control**: Track changes to your calendar_filters.json
5. **Safety first**: Keep `apply_filters_to_conflict_detection: false` to avoid double-booking
6. **Review regularly**: Audit filters monthly to ensure they match your current workflow

## Additional Resources

- [Google Calendar API Event Types](https://developers.google.com/calendar/api/v3/reference/events)
- [Regex Tutorial](https://regexone.com/)
- [Google Calendar Color IDs](https://developers.google.com/calendar/api/guides/colors)

## Need Help?

If you're having trouble configuring filters:
1. Check the troubleshooting section above
2. Review the common examples for similar use cases
3. Test regex patterns using online tools
4. Start with `"enabled": false` and add filters incrementally
