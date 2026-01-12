# API Documentation

Complete reference for all tools provided by the custom task server.

## Tools Overview

| Tool | Description | Write Access Required |
|------|-------------|----------------------|
| `task_list` | List all tasks with filtering | No |
| `task_get` | Get details of a specific task | No |
| `task_create` | Create a new task | Yes |
| `task_update` | Update an existing task | Yes |
| `task_delete` | Delete a task | Yes |

---

## task_list

List all tasks with optional filtering.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `status` | string | No | `"active"` | Filter by status: `"active"`, `"completed"`, or `"all"` |
| `limit` | number | No | `10` | Maximum tasks to return (1-100) |
| `priority` | string | No | - | Filter by priority: `"low"`, `"medium"`, or `"high"` |

### Returns

```json
{
  "tasks": [
    {
      "id": "task-1",
      "title": "Task title",
      "description": "Task description",
      "status": "active",
      "priority": "high",
      "created_at": "2024-01-11T12:00:00Z",
      "completed_at": null
    }
  ],
  "count": 1,
  "filters": {
    "status": "active",
    "limit": 10
  }
}
```

### Example

```python
result = await manager.call_tool('task_list', {
    'status': 'active',
    'limit': 5,
    'priority': 'high'
})
```

---

## task_get

Get detailed information about a specific task.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `task_id` | string | Yes | The unique task identifier |

### Returns

```json
{
  "id": "task-1",
  "title": "Task title",
  "description": "Task description",
  "status": "active",
  "priority": "high",
  "created_at": "2024-01-11T12:00:00Z",
  "completed_at": null
}
```

### Example

```python
result = await manager.call_tool('task_get', {
    'task_id': 'task-1'
})
```

### Errors

- `Task not found: {task_id}` - Task does not exist

---

## task_create

Create a new task. **Requires `ALLOW_WRITE=true`**.

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | Yes | - | Task title (1-200 characters) |
| `description` | string | No | - | Task description (max 2000 characters) |
| `priority` | string | No | `"medium"` | Priority: `"low"`, `"medium"`, or `"high"` |

### Returns

```json
{
  "message": "Task created successfully",
  "task": {
    "id": "task-123",
    "title": "New task",
    "description": "Task description",
    "status": "active",
    "priority": "medium",
    "created_at": "2024-01-11T12:00:00Z"
  }
}
```

### Example

```python
result = await manager.call_tool('task_create', {
    'title': 'Implement new feature',
    'description': 'Add user authentication',
    'priority': 'high'
})
```

### Errors

- `Write access not enabled` - `ALLOW_WRITE` environment variable not set
- Validation errors for invalid parameters

---

## task_update

Update an existing task. **Requires `ALLOW_WRITE=true`**.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `task_id` | string | Yes | The unique task identifier |
| `title` | string | No | New task title (1-200 characters) |
| `description` | string | No | New task description (max 2000 characters) |
| `status` | string | No | New status: `"active"` or `"completed"` |
| `priority` | string | No | New priority: `"low"`, `"medium"`, or `"high"` |

**Note:** Only provided fields will be updated. Others remain unchanged.

### Returns

```json
{
  "message": "Task updated successfully",
  "task": {
    "id": "task-1",
    "title": "Updated title",
    "description": "Updated description",
    "status": "completed",
    "priority": "high",
    "created_at": "2024-01-11T12:00:00Z",
    "completed_at": "2024-01-11T13:00:00Z"
  }
}
```

### Example

```python
result = await manager.call_tool('task_update', {
    'task_id': 'task-1',
    'status': 'completed'
})
```

### Errors

- `Write access not enabled` - `ALLOW_WRITE` environment variable not set
- `Task not found: {task_id}` - Task does not exist
- Validation errors for invalid parameters

---

## task_delete

Delete a task. **Requires `ALLOW_WRITE=true`**.

**Warning:** This action is permanent and cannot be undone.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `task_id` | string | Yes | The unique task identifier |

### Returns

```json
{
  "message": "Task deleted successfully",
  "task_id": "task-1"
}
```

### Example

```python
result = await manager.call_tool('task_delete', {
    'task_id': 'task-1'
})
```

### Errors

- `Write access not enabled` - `ALLOW_WRITE` environment variable not set
- `Task not found: {task_id}` - Task does not exist

---

## Error Handling

All tools return errors in a consistent format:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Error: Detailed error message"
    }
  ],
  "isError": true
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Write access not enabled` | `ALLOW_WRITE` not set | Set `ALLOW_WRITE=true` in environment |
| `Task not found: {id}` | Invalid task ID | Check task ID is correct |
| `Validation error` | Invalid parameters | Check parameter types and constraints |
| `Unknown tool: {name}` | Invalid tool name | Check tool name is correct |

---

## Rate Limiting

Currently no rate limiting is implemented. For production use, consider adding:

- Per-user rate limits
- Per-tool rate limits
- Global rate limits

---

## Authentication

Authentication is handled via the `TASK_API_KEY` environment variable. This key is passed to all API requests.

In production:
- Keep API keys secure
- Rotate keys regularly
- Use different keys for development/production
- Never commit keys to version control

---

## Best Practices

### 1. Error Handling

Always wrap tool calls in try-catch:

```python
try:
    result = await manager.call_tool('task_get', {'task_id': 'task-1'})
    if result.success:
        # Handle success
        pass
    else:
        # Handle failure
        pass
except Exception as e:
    # Handle exceptions
    pass
```

### 2. Input Validation

The server validates all inputs, but you should also validate on the client side for better UX.

### 3. Write Operations

Always set `ALLOW_WRITE=true` explicitly when write operations are needed. Don't leave it enabled by default.

### 4. Batch Operations

For multiple operations, consider batching:

```python
# Get multiple tasks efficiently
task_ids = ['task-1', 'task-2', 'task-3']
tasks = []
for task_id in task_ids:
    result = await manager.call_tool('task_get', {'task_id': task_id})
    if result.success:
        tasks.append(result.data)
```

---

## Migration Guide

If you're migrating from a direct adapter:

1. Update configuration to use MCP bridge
2. Test all tools work correctly
3. Compare performance
4. Update any tool-specific error handling
5. Deploy gradually with monitoring

See [custom-mcp-server-guide.md](../../../docs/custom-mcp-server-guide.md) for full migration instructions.
