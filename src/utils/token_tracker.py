"""
Token Tracker Module - Phase 1 Implementation
Tracks token usage for before/after comparison to measure context reduction effectiveness.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json
from collections import defaultdict
import logfire


class TokenTracker:
    """Track token usage for before/after comparison"""
    
    def __init__(self):
        # Track usage by session and state
        self.baseline_usage: Dict[str, Dict[str, int]] = defaultdict(dict)  # Before context builder
        self.optimized_usage: Dict[str, Dict[str, int]] = defaultdict(dict)  # After context builder
        
        # Track timestamps for reporting
        self.session_start_times: Dict[str, datetime] = {}
        self.session_end_times: Dict[str, datetime] = {}
    
    async def track_baseline(self, session_id: str, state: str, user_tokens: int, system_tokens: int = 0) -> None:
        """Track token usage before optimization
        
        Args:
            session_id: Session identifier
            state: Current state
            user_tokens: Tokens in user message/prompt
            system_tokens: Tokens in system prompt
        """
        total_tokens = user_tokens + system_tokens
        self.baseline_usage[session_id][state] = {
            "user": user_tokens,
            "system": system_tokens,
            "total": total_tokens
        }
        
        # Record session start time if first tracking
        if session_id not in self.session_start_times:
            self.session_start_times[session_id] = datetime.utcnow()
        
        # Log to Logfire
        logfire.info(
            "baseline_token_usage",
            session_id=session_id,
            state=state,
            user_tokens=user_tokens,
            system_tokens=system_tokens,
            total_tokens=total_tokens,
            context_type="full"
        )
    
    async def track_optimized(self, session_id: str, state: str, user_tokens: int, system_tokens: int = 0) -> None:
        """Track token usage after optimization
        
        Args:
            session_id: Session identifier
            state: Current state
            user_tokens: Tokens in user message/prompt
            system_tokens: Tokens in system prompt
        """
        total_tokens = user_tokens + system_tokens
        self.optimized_usage[session_id][state] = {
            "user": user_tokens,
            "system": system_tokens,
            "total": total_tokens
        }
        
        # Update session end time
        self.session_end_times[session_id] = datetime.utcnow()
    
    def get_savings_report(self, session_id: str) -> Dict[str, Any]:
        """Calculate token savings for a specific session"""
        baseline = self.baseline_usage.get(session_id, {})
        optimized = self.optimized_usage.get(session_id, {})
        
        # Calculate totals
        total_baseline = sum(
            v["total"] if isinstance(v, dict) else v 
            for v in baseline.values()
        )
        total_optimized = sum(
            v["total"] if isinstance(v, dict) else v 
            for v in optimized.values()
        )
        
        report = {
            "session_id": session_id,
            "states": {},
            "total_baseline": total_baseline,
            "total_optimized": total_optimized,
            "total_savings": 0,
            "percentage_saved": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Calculate per-state savings
        all_states = set(baseline.keys()) | set(optimized.keys())
        for state in all_states:
            baseline_data = baseline.get(state, {})
            optimized_data = optimized.get(state, {})
            
            # Handle both old (int) and new (dict) formats
            if isinstance(baseline_data, dict):
                baseline_tokens = baseline_data.get("total", 0)
                baseline_user = baseline_data.get("user", 0)
                baseline_system = baseline_data.get("system", 0)
            else:
                baseline_tokens = baseline_data
                baseline_user = baseline_data
                baseline_system = 0
                
            if isinstance(optimized_data, dict):
                optimized_tokens = optimized_data.get("total", 0)
                optimized_user = optimized_data.get("user", 0)
                optimized_system = optimized_data.get("system", 0)
            else:
                optimized_tokens = optimized_data
                optimized_user = optimized_data
                optimized_system = 0
            
            if baseline_tokens > 0:
                saved = baseline_tokens - optimized_tokens
                percentage = (saved / baseline_tokens * 100)
            else:
                saved = 0
                percentage = 0
            
            report["states"][state] = {
                "baseline": {
                    "user": baseline_user,
                    "system": baseline_system,
                    "total": baseline_tokens
                },
                "optimized": {
                    "user": optimized_user,
                    "system": optimized_system,
                    "total": optimized_tokens
                },
                "saved": saved,
                "percentage": round(percentage, 1)
            }
        
        # Calculate total savings
        if report["total_baseline"] > 0:
            report["total_savings"] = report["total_baseline"] - report["total_optimized"]
            report["percentage_saved"] = round(
                (report["total_savings"] / report["total_baseline"]) * 100, 1
            )
        
        return report
    
    def get_aggregate_report(self) -> Dict[str, Any]:
        """Get aggregate report across all sessions"""
        
        # Aggregate by state across all sessions
        state_totals_baseline = defaultdict(int)
        state_totals_optimized = defaultdict(int)
        
        for session_id in self.baseline_usage:
            for state, tokens in self.baseline_usage[session_id].items():
                state_totals_baseline[state] += tokens
        
        for session_id in self.optimized_usage:
            for state, tokens in self.optimized_usage[session_id].items():
                state_totals_optimized[state] += tokens
        
        # Calculate aggregate stats
        total_baseline = sum(state_totals_baseline.values())
        total_optimized = sum(state_totals_optimized.values())
        
        report = {
            "total_sessions": len(set(self.baseline_usage.keys()) | set(self.optimized_usage.keys())),
            "states": {},
            "total_baseline_tokens": total_baseline,
            "total_optimized_tokens": total_optimized,
            "total_tokens_saved": total_baseline - total_optimized,
            "average_percentage_saved": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Per-state aggregate stats
        all_states = set(state_totals_baseline.keys()) | set(state_totals_optimized.keys())
        for state in sorted(all_states):
            baseline = state_totals_baseline.get(state, 0)
            optimized = state_totals_optimized.get(state, 0)
            
            if baseline > 0:
                saved = baseline - optimized
                percentage = (saved / baseline * 100)
            else:
                saved = 0
                percentage = 0
            
            report["states"][state] = {
                "total_baseline": baseline,
                "total_optimized": optimized,
                "total_saved": saved,
                "percentage_saved": round(percentage, 1)
            }
        
        # Calculate average percentage saved
        if total_baseline > 0:
            report["average_percentage_saved"] = round(
                ((total_baseline - total_optimized) / total_baseline) * 100, 1
            )
        
        return report
    
    def print_session_report(self, session_id: str) -> None:
        """Print a formatted report for a session"""
        report = self.get_savings_report(session_id)
        
        print(f"\n{'='*60}")
        print(f"Token Usage Report - Session: {session_id[:8]}...")
        print(f"{'='*60}")
        print(f"Total Baseline Tokens: {report['total_baseline']:,}")
        print(f"Total Optimized Tokens: {report['total_optimized']:,}")
        print(f"Total Tokens Saved: {report['total_savings']:,}")
        print(f"Percentage Saved: {report['percentage_saved']}%")
        print(f"\nPer-State Breakdown:")
        print(f"{'State':<30} {'Baseline':>10} {'Optimized':>10} {'Saved':>10} {'%':>6}")
        print(f"{'-'*70}")
        
        for state, data in sorted(report['states'].items()):
            print(f"{state:<30} {data['baseline']:>10,} {data['optimized']:>10,} "
                  f"{data['saved']:>10,} {data['percentage']:>5.1f}%")
    
    def print_aggregate_report(self) -> None:
        """Print a formatted aggregate report"""
        report = self.get_aggregate_report()
        
        print(f"\n{'='*60}")
        print(f"Aggregate Token Usage Report - {report['total_sessions']} Sessions")
        print(f"{'='*60}")
        print(f"Total Baseline Tokens: {report['total_baseline_tokens']:,}")
        print(f"Total Optimized Tokens: {report['total_optimized_tokens']:,}")
        print(f"Total Tokens Saved: {report['total_tokens_saved']:,}")
        print(f"Average Percentage Saved: {report['average_percentage_saved']}%")
        print(f"\nPer-State Aggregate:")
        print(f"{'State':<30} {'Baseline':>12} {'Optimized':>12} {'Saved':>12} {'%':>6}")
        print(f"{'-'*74}")
        
        for state, data in sorted(report['states'].items()):
            print(f"{state:<30} {data['total_baseline']:>12,} {data['total_optimized']:>12,} "
                  f"{data['total_saved']:>12,} {data['percentage_saved']:>5.1f}%")
    
    def export_report(self, filepath: str, session_id: Optional[str] = None) -> None:
        """Export report to JSON file"""
        if session_id:
            report = self.get_savings_report(session_id)
        else:
            report = self.get_aggregate_report()
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report exported to: {filepath}")
    
    async def track_modular(
        self,
        session_id: str,
        state: str,
        user_tokens: int,
        system_tokens: int
    ):
        """Track token usage for modular system"""
        logfire.info(
            "modular_token_usage",
            session_id=session_id,
            state=state,
            user_tokens=user_tokens,
            system_tokens=system_tokens,
            total_tokens=user_tokens + system_tokens,
            prompt_type="modular"
        )
    
    async def track_quality_metrics(
        self,
        session_id: str,
        state: str,
        prompt_type: str,  # "modular" or "monolithic"
        metrics: Dict[str, Any]
    ):
        """Track quality metrics for comparison"""
        logfire.info(
            "quality_metrics",
            session_id=session_id,
            state=state,
            prompt_type=prompt_type,
            **metrics
        )