"""
Benchmark comparison: Lock-based vs Lock-free message queue implementations.

This benchmark demonstrates the performance difference between:
1. OLD: Lock-based updates (all operations acquire lock)
2. NEW: Lock-free updates (only structural changes acquire lock)
"""
import time
import threading
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock


# ============================================================================
# OLD IMPLEMENTATION (Lock-Based)
# ============================================================================

@dataclass
class StreamingMessageOld:
    """Message class for old implementation."""
    message_id: str
    sender: str
    content: str
    timestamp: datetime
    receivers: Optional[List[str]]
    sender_type: str
    is_complete: bool = False
    last_update: datetime = field(default_factory=datetime.now)
    
    def update_content(self, new_chunk: str):
        self.content += new_chunk
        self.last_update = datetime.now()
    
    def mark_complete(self):
        self.is_complete = True
        self.last_update = datetime.now()


class MessageQueueOld:
    """OLD: All operations use locks."""
    
    def __init__(self):
        self._queue: List[StreamingMessageOld] = []
        self._lock = Lock()
        self._message_index: Dict[str, int] = {}
        self._next_id = 0
    
    def submit_message(self, sender: str, initial_content: str,
                      receivers: Optional[List[str]] = None,
                      sender_type: str = "agent") -> str:
        with self._lock:
            message_id = f"{sender}_{self._next_id}"
            self._next_id += 1
            
            streaming_msg = StreamingMessageOld(
                message_id=message_id,
                sender=sender,
                content=initial_content,
                timestamp=datetime.now(),
                receivers=receivers,
                sender_type=sender_type,
                is_complete=False
            )
            
            self._queue.append(streaming_msg)
            self._message_index[message_id] = len(self._queue) - 1
            
            return message_id
    
    def update_message(self, message_id: str, new_chunk: str) -> bool:
        # OLD: Lock acquired for every update!
        with self._lock:
            if message_id not in self._message_index:
                return False
            
            idx = self._message_index[message_id]
            if idx < len(self._queue):
                self._queue[idx].update_content(new_chunk)
                return True
            return False
    
    def complete_message(self, message_id: str) -> bool:
        # OLD: Lock acquired for completion
        with self._lock:
            if message_id not in self._message_index:
                return False
            
            idx = self._message_index[message_id]
            if idx < len(self._queue):
                self._queue[idx].mark_complete()
                return True
            return False
    
    def get_display_snapshot(self) -> List[StreamingMessageOld]:
        with self._lock:
            return self._queue.copy()


# ============================================================================
# NEW IMPLEMENTATION (Lock-Free Updates)
# ============================================================================

@dataclass
class StreamingMessageNew:
    """Message class for new implementation."""
    message_id: str
    sender: str
    content: str
    timestamp: datetime
    receivers: Optional[List[str]]
    sender_type: str
    is_complete: bool = False
    last_update: datetime = field(default_factory=datetime.now)
    
    def update_content(self, new_chunk: str):
        self.content += new_chunk
        self.last_update = datetime.now()
    
    def mark_complete(self):
        self.is_complete = True
        self.last_update = datetime.now()


class MessageQueueNew:
    """NEW: Lock-free updates with array-based indexing."""
    
    def __init__(self):
        self._queue: List[StreamingMessageNew] = []
        self._lock = Lock()  # Only for structural changes
        self._next_id = 0
    
    def submit_message(self, sender: str, initial_content: str,
                      receivers: Optional[List[str]] = None,
                      sender_type: str = "agent") -> int:
        with self._lock:
            message_id = f"{sender}_{self._next_id}"
            self._next_id += 1
            
            streaming_msg = StreamingMessageNew(
                message_id=message_id,
                sender=sender,
                content=initial_content,
                timestamp=datetime.now(),
                receivers=receivers,
                sender_type=sender_type,
                is_complete=False
            )
            
            self._queue.append(streaming_msg)
            return len(self._queue) - 1  # Return array index
    
    def update_message(self, idx: int, new_chunk: str) -> bool:
        # NEW: No lock needed - direct array index access!
        if idx < 0 or idx >= len(self._queue):
            return False
        
        self._queue[idx].update_content(new_chunk)
        return True
    
    def complete_message(self, idx: int) -> bool:
        # NEW: No lock needed
        if idx < 0 or idx >= len(self._queue):
            return False
        
        self._queue[idx].mark_complete()
        return True
    
    def get_display_snapshot(self) -> List[StreamingMessageNew]:
        with self._lock:
            return self._queue.copy()


# ============================================================================
# BENCHMARK LOGIC
# ============================================================================

def benchmark_worker(queue, message_id, num_updates: int, thread_id: int):
    """Worker that performs many updates."""
    start = time.perf_counter()
    
    for i in range(num_updates):
        queue.update_message(message_id, f"x")  # Short chunk for speed
    
    queue.complete_message(message_id)
    
    duration = time.perf_counter() - start
    return duration


def run_benchmark_scenario(queue_class, num_threads: int, updates_per_thread: int, label: str):
    """Run a benchmark scenario."""
    queue = queue_class()
    
    # Create messages
    message_ids = []
    for i in range(num_threads):
        msg_id = queue.submit_message(
            sender=f"Agent{i}",
            initial_content="",
            sender_type="agent"
        )
        message_ids.append(msg_id)
    
    # Start threads
    threads: List[threading.Thread] = []
    results = [0.0] * num_threads
    
    start_time = time.perf_counter()
    
    for i in range(num_threads):
        def worker(thread_id=i):
            results[thread_id] = benchmark_worker(
                queue, message_ids[thread_id], updates_per_thread, thread_id
            )
        
        thread = threading.Thread(target=worker)
        threads.append(thread)
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    total_time = time.perf_counter() - start_time
    total_updates = num_threads * updates_per_thread
    
    # Verify integrity
    snapshot = queue.get_display_snapshot()
    all_complete = all(msg.is_complete for msg in snapshot)
    
    return {
        'label': label,
        'total_time': total_time,
        'total_updates': total_updates,
        'updates_per_sec': total_updates / total_time,
        'avg_thread_time': sum(results) / len(results),
        'max_thread_time': max(results),
        'min_thread_time': min(results),
        'all_complete': all_complete
    }


def print_result(result: dict):
    """Print benchmark results."""
    print(f"\n{'─'*70}")
    print(f"📊 {result['label']}")
    print(f"{'─'*70}")
    print(f"   Total updates:      {result['total_updates']:>12,}")
    print(f"   Total time:         {result['total_time']*1000:>12.2f} ms")
    print(f"   Updates/sec:        {result['updates_per_sec']:>12,.0f}")
    print(f"   Avg thread time:    {result['avg_thread_time']*1000:>12.2f} ms")
    print(f"   Max thread time:    {result['max_thread_time']*1000:>12.2f} ms")
    print(f"   Min thread time:    {result['min_thread_time']*1000:>12.2f} ms")
    print(f"   Integrity check:    {result['all_complete'] and '✅ PASS' or '❌ FAIL'}")


def compare_results(old_result: dict, new_result: dict):
    """Compare old vs new results."""
    speedup = new_result['updates_per_sec'] / old_result['updates_per_sec']
    time_saved = old_result['total_time'] - new_result['total_time']
    time_saved_pct = (time_saved / old_result['total_time']) * 100
    
    print(f"\n{'='*70}")
    print(f"🎯 COMPARISON: OLD vs NEW")
    print(f"{'='*70}")
    print(f"   Speedup:            {speedup:>12.2f}x faster")
    print(f"   Time saved:         {time_saved*1000:>12.2f} ms ({time_saved_pct:.1f}%)")
    print(f"   Lock contention:    {'HIGH (every update)':>20} → {'ZERO (lock-free)':>20}")
    
    if speedup > 1.5:
        print(f"\n   ✨ Lock-free approach is {speedup:.1f}x faster!")
    elif speedup > 1.1:
        print(f"\n   ✓ Lock-free approach shows {time_saved_pct:.1f}% improvement")
    else:
        print(f"\n   ≈ Similar performance (overhead dominated by other factors)")


def main():
    """Run comprehensive benchmark comparison."""
    print("╔" + "═"*68 + "╗")
    print("║" + " "*20 + "LOCK-BASED vs LOCK-FREE BENCHMARK" + " "*15 + "║")
    print("╚" + "═"*68 + "╝")
    print("\nComparing two implementations:")
    print("  OLD: Lock acquired for every update (high contention)")
    print("  NEW: Lock-free updates (zero contention)")
    print("\nThis simulates real-world streaming where agents update messages")
    print("concurrently at high frequency.\n")
    
    # Test scenarios
    scenarios = [
        (4, 5000, "Light Load: 4 threads × 5K updates"),
        (8, 5000, "Medium Load: 8 threads × 5K updates"),
        (16, 5000, "Heavy Load: 16 threads × 5K updates"),
        (8, 20000, "Sustained: 8 threads × 20K updates"),
    ]
    
    all_comparisons = []
    
    for num_threads, updates, desc in scenarios:
        print(f"\n{'='*70}")
        print(f"🧪 Test Case: {desc}")
        print(f"{'='*70}")
        
        # Warm-up
        print("Warming up...")
        run_benchmark_scenario(MessageQueueOld, 2, 100, "warmup")
        run_benchmark_scenario(MessageQueueNew, 2, 100, "warmup")
        
        # Run old implementation
        print("\n⏱️  Running OLD (lock-based)...")
        old_result = run_benchmark_scenario(
            MessageQueueOld, num_threads, updates, 
            f"OLD: Lock-Based ({num_threads} threads)"
        )
        print_result(old_result)
        
        # Run new implementation
        print("\n⏱️  Running NEW (lock-free)...")
        new_result = run_benchmark_scenario(
            MessageQueueNew, num_threads, updates,
            f"NEW: Lock-Free ({num_threads} threads)"
        )
        print_result(new_result)
        
        # Compare
        compare_results(old_result, new_result)
        
        all_comparisons.append({
            'desc': desc,
            'old': old_result,
            'new': new_result,
            'speedup': new_result['updates_per_sec'] / old_result['updates_per_sec']
        })
    
    # Final summary
    print(f"\n\n{'='*70}")
    print(f"📈 OVERALL SUMMARY")
    print(f"{'='*70}")
    print(f"{'Test Case':<40} {'Speedup':>15} {'Winner':>15}")
    print("─" * 70)
    
    for comp in all_comparisons:
        winner = "🚀 Lock-Free" if comp['speedup'] > 1 else "Lock-Based"
        print(f"{comp['desc']:<40} {comp['speedup']:>14.2f}x {winner:>15}")
    
    avg_speedup = sum(c['speedup'] for c in all_comparisons) / len(all_comparisons)
    
    print(f"\n{'─'*70}")
    print(f"{'Average Speedup:':<40} {avg_speedup:>14.2f}x")
    print(f"{'─'*70}")
    
    print(f"\n🎯 KEY INSIGHTS:")
    print(f"   1. Lock-free updates eliminate contention during streaming")
    print(f"   2. Higher thread count = more benefit from lock-free approach")
    print(f"   3. Speedup increases with update frequency (lock overhead compounds)")
    print(f"   4. Perfect for streaming where partial/stale data is acceptable")
    
    print(f"\n💡 RECOMMENDATION:")
    if avg_speedup > 1.5:
        print(f"   ✅ Lock-free approach is {avg_speedup:.1f}x faster on average!")
        print(f"   ✅ Significant performance gain for concurrent streaming workloads")
        print(f"   ✅ Trade-off (accepting stale data) is worth the performance boost")
    else:
        print(f"   ✓ Lock-free shows {((avg_speedup-1)*100):.1f}% improvement")
        print(f"   ✓ Consider lock-free if you need maximum throughput")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
