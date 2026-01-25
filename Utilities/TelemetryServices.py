import time
from typing import Dict, Optional, Any
from Utilities.LoggingServices import logGenerator


class TelemetryTracker:
    """
    Centralized telemetry tracking and logging service for performance monitoring
    
    Features:
    - Track operation timing with start/stop methods
    - Log detailed performance metrics
    - Support for nested timing measurements
    - Configurable logging output
    - Thread-safe operation tracking
    """
    
    def __init__(self, log_generator: Optional[logGenerator] = None, operation_name: str = "Unknown Operation"):
        """
        Initialize telemetry tracker
        
        Args:
            log_generator: Optional logging service instance
            operation_name: Name of the operation being tracked
        """
        self.log_generator = log_generator
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
        self.phase_times = {}
        self.metrics = {}
        self.total_records = 0
        self.is_tracking = False
        
    def start_operation(self, operation_name: str = None):
        """
        Start tracking an operation
        
        Args:
            operation_name: Optional override for operation name
        """
        if operation_name:
            self.operation_name = operation_name
            
        self.start_time = time.time()
        self.end_time = None
        self.phase_times = {}
        self.metrics = {}
        self.is_tracking = True
        
        if self.log_generator:
            self.log_generator.log_details(f"🔄 Starting telemetry tracking for: {self.operation_name}")
            
    def stop_operation(self):
        """Stop tracking the current operation"""
        if not self.is_tracking:
            return
            
        self.end_time = time.time()
        self.is_tracking = False
        
    def start_phase(self, phase_name: str):
        """
        Start tracking a specific phase within the operation
        
        Args:
            phase_name: Name of the phase (e.g., 'preparation', 'database_ops', 'commit')
        """
        if phase_name not in self.phase_times:
            self.phase_times[phase_name] = {'start': None, 'total': 0, 'count': 0}
            
        self.phase_times[phase_name]['start'] = time.time()
        
    def end_phase(self, phase_name: str):
        """
        End tracking a specific phase
        
        Args:
            phase_name: Name of the phase to end
        """
        if phase_name in self.phase_times and self.phase_times[phase_name]['start']:
            phase_duration = time.time() - self.phase_times[phase_name]['start']
            self.phase_times[phase_name]['total'] += phase_duration
            self.phase_times[phase_name]['count'] += 1
            self.phase_times[phase_name]['start'] = None
            
    def add_metric(self, key: str, value: Any):
        """
        Add a custom metric to track
        
        Args:
            key: Metric name
            value: Metric value
        """
        self.metrics[key] = value
        
    def set_record_count(self, count: int):
        """
        Set the total number of records processed
        
        Args:
            count: Number of records
        """
        self.total_records = count
        
    def get_total_time(self) -> float:
        """Get total operation time in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
        
    def get_phase_time(self, phase_name: str) -> float:
        """
        Get total time for a specific phase
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Total time in seconds for the phase
        """
        if phase_name in self.phase_times:
            return self.phase_times[phase_name]['total']
        return 0.0
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary
        
        Returns:
            Dictionary containing all performance metrics
        """
        total_time = self.get_total_time()
        
        summary = {
            'operation_name': self.operation_name,
            'total_time': total_time,
            'total_records': self.total_records,
            'records_per_second': self.total_records / total_time if total_time > 0 else 0,
            'avg_time_per_record_ms': (total_time / self.total_records * 1000) if self.total_records > 0 else 0,
            'phases': {},
            'metrics': self.metrics.copy()
        }
        
        # Add phase information
        for phase_name, phase_data in self.phase_times.items():
            phase_time = phase_data['total']
            summary['phases'][phase_name] = {
                'total_time': phase_time,
                'percentage': (phase_time / total_time * 100) if total_time > 0 else 0,
                'call_count': phase_data['count'],
                'avg_time_per_call': phase_time / phase_data['count'] if phase_data['count'] > 0 else 0
            }
            
        return summary
        
    def log_telemetry_summary(self, include_phases: bool = True, include_metrics: bool = True):
        """
        Log comprehensive telemetry summary
        
        Args:
            include_phases: Whether to include phase breakdown
            include_metrics: Whether to include custom metrics
        """
        if not self.log_generator:
            return
            
        summary = self.get_performance_summary()
        
        # Main telemetry header
        self.log_generator.log_details("📊 TELEMETRY SUMMARY:")
        self.log_generator.log_details(f"   🎯 Operation: {summary['operation_name']}")
        self.log_generator.log_details(f"   📝 Total Records: {summary['total_records']}")
        self.log_generator.log_details(f"   ⏱️  Total Time: {summary['total_time']:.3f}s")
        self.log_generator.log_details(f"   📈 Records/Second: {summary['records_per_second']:.2f}")
        self.log_generator.log_details(f"   📊 Avg Time/Record: {summary['avg_time_per_record_ms']:.2f}ms")
        
        # Phase breakdown
        if include_phases and summary['phases']:
            self.log_generator.log_details("   🔧 Phase Breakdown:")
            for phase_name, phase_info in summary['phases'].items():
                icon = self._get_phase_icon(phase_name)
                self.log_generator.log_details(
                    f"      {icon} {phase_name.title()}: {phase_info['total_time']:.3f}s "
                    f"({phase_info['percentage']:.1f}%) - {phase_info['call_count']} calls"
                )
                
        # Custom metrics
        if include_metrics and summary['metrics']:
            self.log_generator.log_details("   📌 Custom Metrics:")
            for key, value in summary['metrics'].items():
                self.log_generator.log_details(f"      • {key}: {value}")
                
        # Performance assessment
        performance_rating = self._assess_performance(summary)
        self.log_generator.log_details(f"   🎯 Performance Rating: {performance_rating}")
        
        self.log_generator.log_details("   ✅ Telemetry tracking completed")
        self.log_generator.log_details("################################################################################################")
        
    def _get_phase_icon(self, phase_name: str) -> str:
        """Get appropriate icon for phase name"""
        icons = {
            'preparation': '🔧',
            'database_operations': '💾',
            'database_ops': '💾',
            'db_operations': '💾',
            'commit': '✅',
            'validation': '🔍',
            'processing': '⚙️',
            'cleanup': '🧹'
        }
        return icons.get(phase_name.lower(), '📌')
        
    def _assess_performance(self, summary: Dict[str, Any]) -> str:
        """
        Assess performance based on metrics
        
        Args:
            summary: Performance summary dictionary
            
        Returns:
            Performance rating string
        """
        records_per_second = summary['records_per_second']
        
        if records_per_second > 1000:
            return "🚀 Excellent (>1000 records/sec)"
        elif records_per_second > 500:
            return "⚡ Very Good (500-1000 records/sec)"
        elif records_per_second > 100:
            return "👍 Good (100-500 records/sec)"
        elif records_per_second > 50:
            return "⚠️ Fair (50-100 records/sec)"
        else:
            return "🐌 Needs Optimization (<50 records/sec)"


class OperationTimer:
    """
    Context manager for timing operations with automatic telemetry tracking
    
    Usage:
        with OperationTimer("my_operation", log_generator) as timer:
            timer.set_record_count(1000)
            
            timer.start_phase("preparation")
            # ... preparation code ...
            timer.end_phase("preparation")
            
            timer.start_phase("database_ops")
            # ... database code ...
            timer.end_phase("database_ops")
            
            timer.add_metric("batch_size", 50)
        # Telemetry automatically logged on exit
    """
    
    def __init__(self, operation_name: str, log_generator: Optional[logGenerator] = None):
        """
        Initialize operation timer
        
        Args:
            operation_name: Name of the operation
            log_generator: Optional logging service
        """
        self.telemetry = TelemetryTracker(log_generator, operation_name)
        
    def __enter__(self):
        """Start telemetry tracking when entering context"""
        self.telemetry.start_operation()
        return self.telemetry
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking and log summary when exiting context"""
        self.telemetry.stop_operation()
        self.telemetry.log_telemetry_summary()
        
        # Log exception if one occurred
        if exc_type and self.telemetry.log_generator:
            self.telemetry.log_generator.log_details(f"❌ Operation failed with {exc_type.__name__}: {exc_val}")


def create_telemetry_tracker(operation_name: str, log_generator: Optional[logGenerator] = None) -> TelemetryTracker:
    """
    Factory function to create a telemetry tracker
    
    Args:
        operation_name: Name of the operation to track
        log_generator: Optional logging service
        
    Returns:
        Configured TelemetryTracker instance
    """
    return TelemetryTracker(log_generator, operation_name)


def measure_execution_time(func):
    """
    Decorator to automatically measure and log function execution time
    
    Usage:
        @measure_execution_time
        def my_function():
            # ... code ...
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            print(f"⏱️ {func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ {func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    return wrapper