#!/usr/bin/env python3
"""
CLI tool for ModelEscalator feedback and metrics.

Usage:
    # Record feedback on last model choice
    ./escalator_cli.py feedback --rating 3 --comment "Just right"
    
    # View metrics
    ./escalator_cli.py metrics --days 7
    
    # Train from feedback
    ./escalator_cli.py train
    
    # View switch history
    ./escalator_cli.py history --conversation main-session
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.model_escalator_v2 import (
    get_escalator_v2,
    record_model_feedback,
    get_escalation_metrics
)


def cmd_feedback(args):
    """Record feedback on model choice."""
    escalator = get_escalator_v2()
    
    # Get last conversation from state
    cursor = escalator.conn.cursor()
    cursor.execute('''
        SELECT conversation_id, current_model, complexity_score
        FROM conversation_state
        ORDER BY last_model_switch_time DESC
        LIMIT 1
    ''')
    
    result = cursor.fetchone()
    if not result:
        print("No recent conversations found")
        return
    
    conversation_id, model, complexity = result
    
    # Record feedback
    record_model_feedback(
        conversation_id=args.conversation or conversation_id,
        message=args.message or "Recent message",
        model=model,
        complexity=complexity,
        rating=args.rating,
        comment=args.comment
    )
    
    print(f"✓ Feedback recorded: rating={args.rating}, model={model}")
    
    # Train if enough samples
    if escalator.train_from_feedback():
        print("✓ Complexity analyzer weights updated from feedback")


def cmd_metrics(args):
    """Display escalation metrics."""
    metrics = get_escalation_metrics(args.days)
    
    print(f"\n📊 Model Escalation Metrics (last {args.days} days)\n")
    print(f"Total escalations: {metrics.get('total_escalations', 0)}")
    print(f"Average complexity: {metrics.get('avg_complexity', 0):.3f}")
    print(f"Feedback count: {metrics.get('feedback_count', 0)}")
    print(f"Average rating: {metrics.get('avg_rating', 0):.2f}/5.0")
    
    print("\nModel usage:")
    for model, count in metrics.get('model_usage', {}).items():
        short_model = model.split('/')[-1] if '/' in model else model
        print(f"  {short_model}: {count}")


def cmd_train(args):
    """Train complexity analyzer from feedback."""
    escalator = get_escalator_v2()
    
    if escalator.train_from_feedback(min_samples=args.min_samples):
        print(f"✓ Trained complexity analyzer from feedback")
        print(f"  Updated feature weights:")
        for feature, weight in escalator.analyzer.feature_weights.items():
            print(f"    {feature}: {weight:.3f}")
    else:
        print(f"Not enough feedback samples (need {args.min_samples})")


def cmd_history(args):
    """Show model switch history."""
    escalator = get_escalator_v2()
    history = escalator.get_switch_history(args.conversation, limit=args.limit)
    
    if not history:
        print(f"No switch history for conversation: {args.conversation}")
        return
    
    print(f"\n📜 Model Switch History: {args.conversation}\n")
    for entry in history:
        timestamp = datetime.fromtimestamp(entry['timestamp'])
        print(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  {entry['from_model']} → {entry['to_model']}")
        print(f"  Complexity: {entry['complexity']:.3f}\n")


def cmd_status(args):
    """Show current escalator status."""
    escalator = get_escalator_v2()
    
    cursor = escalator.conn.cursor()
    cursor.execute('''
        SELECT conversation_id, current_model, complexity_score, turn_count
        FROM conversation_state
        ORDER BY last_model_switch_time DESC
        LIMIT 5
    ''')
    
    print("\n🔄 Active Conversations\n")
    for row in cursor.fetchall():
        conv_id, model, complexity, turns = row
        short_model = model.split('/')[-1] if '/' in model else model
        print(f"{conv_id}:")
        print(f"  Model: {short_model}")
        print(f"  Complexity: {complexity:.3f}")
        print(f"  Turns: {turns}\n")


def main():
    parser = argparse.ArgumentParser(description="ModelEscalator CLI")
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Feedback command
    feedback_parser = subparsers.add_parser('feedback', help='Record feedback')
    feedback_parser.add_argument('--rating', type=int, required=True, choices=[1,2,3,4,5],
                                 help='Rating: 1=too weak, 3=just right, 5=overkill')
    feedback_parser.add_argument('--comment', help='Optional comment')
    feedback_parser.add_argument('--conversation', help='Conversation ID (default: last)')
    feedback_parser.add_argument('--message', help='Message text')
    
    # Metrics command
    metrics_parser = subparsers.add_parser('metrics', help='View metrics')
    metrics_parser.add_argument('--days', type=int, default=7, help='Days to analyze')
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Train from feedback')
    train_parser.add_argument('--min-samples', type=int, default=10,
                             help='Minimum feedback samples required')
    
    # History command
    history_parser = subparsers.add_parser('history', help='View switch history')
    history_parser.add_argument('--conversation', required=True, help='Conversation ID')
    history_parser.add_argument('--limit', type=int, default=10, help='Max entries')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        'feedback': cmd_feedback,
        'metrics': cmd_metrics,
        'train': cmd_train,
        'history': cmd_history,
        'status': cmd_status
    }
    
    commands[args.command](args)


if __name__ == '__main__':
    main()
