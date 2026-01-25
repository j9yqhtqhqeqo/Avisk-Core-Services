"""
Example usage of TelemetryServices in InsightGeneratorDBManager

This file demonstrates how to integrate the new telemetry tracking 
into the existing save methods for performance monitoring.
"""

from Utilities.TelemetryServices import TelemetryTracker, OperationTimer
from Utilities.LoggingServices import logGenerator
import time


# Example 1: Using TelemetryTracker manually
def save_insights_with_manual_telemetry(self, insightList, dictionary_type, document_id, year=0):
    """
    Example of manual telemetry integration
    """
    # Create telemetry tracker
    telemetry = TelemetryTracker(self.log_generator, "save_insights")
    telemetry.start_operation()
    telemetry.set_record_count(len(insightList))
    
    try:
        sector_id = self.get_sector_id(document_id)
        total_records_added_to_db = 0
        
        telemetry.start_phase("preparation")
        # Data preparation logic here
        telemetry.end_phase("preparation")
        
        telemetry.start_phase("database_operations")
        for insight in insightList:
            # Database operations here
            total_records_added_to_db += 1
            
            # Track batch commits
            if total_records_added_to_db % 50 == 0:
                telemetry.start_phase("commit")
                self.dbConnection.commit()
                telemetry.end_phase("commit")
                
        telemetry.end_phase("database_operations")
        
        # Final commit
        telemetry.start_phase("commit")
        if total_records_added_to_db > 0:
            self.dbConnection.commit()
        telemetry.end_phase("commit")
        
        # Add custom metrics
        telemetry.add_metric("Dictionary Type", dictionary_type)
        telemetry.add_metric("Document ID", document_id)
        telemetry.add_metric("Year", year)
        telemetry.add_metric("Batch Size", 50)
        
        telemetry.set_record_count(total_records_added_to_db)
        
    except Exception as exc:
        telemetry.add_metric("Error", str(exc))
        raise exc
    finally:
        telemetry.stop_operation()
        telemetry.log_telemetry_summary()


# Example 2: Using OperationTimer context manager (Recommended)
def save_exp_int_insights_with_context_manager(self, insightList, dictionary_type, document_id):
    """
    Example using OperationTimer context manager - RECOMMENDED APPROACH
    """
    with OperationTimer("save_Exp_Int_Insights", self.log_generator) as timer:
        timer.set_record_count(len(insightList))
        timer.add_metric("Dictionary Type", dictionary_type)
        timer.add_metric("Document ID", document_id)
        
        timer.start_phase("initialization")
        sector_id = self.get_sector_id(document_id)
        total_records_added_to_db = 0
        timer.end_phase("initialization")
        
        timer.start_phase("database_operations")
        for exp_int_insight_entity in insightList:
            timer.start_phase("preparation")
            # Extract entity data
            exp_keyword_hit_id1 = exp_int_insight_entity.exp_keyword_hit_id1
            exp_keyword1 = exp_int_insight_entity.exp_keyword1
            # ... other extractions
            timer.end_phase("preparation")
            
            # Database operation
            cursor = self.dbConnection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            sql = f"INSERT INTO t_exp_int_insights (...)"
            
            cursor.execute(sql)
            total_records_added_to_db += 1
            
            # Batch commit tracking
            if total_records_added_to_db % 50 == 0:
                timer.start_phase("commit")
                self.dbConnection.commit()
                timer.end_phase("commit")
                
        timer.end_phase("database_operations")
        
        # Final commit
        timer.start_phase("commit")
        if total_records_added_to_db > 0:
            self.dbConnection.commit()
            cursor.close()
        timer.end_phase("commit")
        
        timer.set_record_count(total_records_added_to_db)
        timer.add_metric("Batch Commit Frequency", "Every 50 records")


# Example 3: Using the decorator for simple function timing
from Utilities.TelemetryServices import measure_execution_time

@measure_execution_time
def update_sector_stats_with_decorator(self, sector, year, **kwargs):
    """
    Example using simple execution time decorator
    """
    # Your existing update_sector_stats logic here
    pass


# Example 4: Integration pattern for existing methods
def save_insights_integrated_pattern(self, insightList, dictionary_type, document_id, year=0):
    """
    Integration pattern for existing methods - minimal changes required
    """
    # Replace the manual telemetrics with context manager
    with OperationTimer("save_insights", self.log_generator) as timer:
        timer.set_record_count(len(insightList))
        timer.add_metric("Dictionary Type", dictionary_type)
        timer.add_metric("Document ID", document_id)
        timer.add_metric("Year", year)
        
        # Wrap existing phases
        timer.start_phase("initialization")
        insight: Insight
        self.d_next_seed = 0
        total_records_added_to_db = 0
        sector_id = self.get_sector_id(document_id)
        timer.end_phase("initialization")
        
        timer.start_phase("database_operations")
        
        for insight in insightList:
            timer.start_phase("preparation")
            # Existing data extraction code
            key_word_hit_id1 = insight.keyword_hit_id1
            key_word_hit_id2 = insight.keyword_hit_id2
            # ... rest of extraction
            timer.end_phase("preparation")
            
            # Existing database code with commit tracking
            cursor = self.dbConnection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Existing SQL logic
            if (dictionary_type == Lookups().Exposure_Pathway_Dictionary_Type):
                sql = f"INSERT INTO t_exposure_pathway_insights (...)"
            # ... other SQL cases
            
            try:
                cursor.execute(sql)
                total_records_added_to_db += 1
                
                if (total_records_added_to_db % 50 == 0):
                    timer.start_phase("commit")
                    self.dbConnection.commit()
                    timer.end_phase("commit")
                    
            except Exception as exc:
                self.dbConnection.rollback()
                timer.add_metric("Error", str(exc))
                raise exc
                
        timer.end_phase("database_operations")
        
        # Final commit
        timer.start_phase("commit")
        if (total_records_added_to_db > 0):
            self.dbConnection.commit()
            cursor.close()
        timer.end_phase("commit")
        
        timer.set_record_count(total_records_added_to_db)
        timer.add_metric("Batch Commit Frequency", "Every 50 records")
        
    # Telemetry is automatically logged when exiting the context manager


# Example 5: Bulk operations with enhanced telemetry
def save_insights_bulk_with_telemetry(self, insightList, dictionary_type, document_id, year=0):
    """
    Example of bulk insert with comprehensive telemetry tracking
    """
    with OperationTimer("save_insights_bulk", self.log_generator) as timer:
        timer.set_record_count(len(insightList))
        timer.add_metric("Operation Type", "Bulk Insert")
        timer.add_metric("Dictionary Type", dictionary_type)
        
        timer.start_phase("initialization")
        sector_id = self.get_sector_id(document_id)
        insert_data = []
        timer.end_phase("initialization")
        
        timer.start_phase("preparation")
        # Prepare bulk insert data
        for insight in insightList:
            insert_data.append((
                insight.document_id,
                sector_id,
                insight.document_name,
                insight.keyword_hit_id1,
                insight.keyword_hit_id2,
                insight.keyword1,
                insight.keyword2,
                insight.score,
                insight.factor1,
                insight.factor2,
                insight.exposure_path_id,
                year,
                'Mohan Hanumantha',
                'Mohan Hanumantha'
            ))
        timer.end_phase("preparation")
        
        timer.start_phase("database_operations")
        cursor = self.dbConnection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        sql = """INSERT INTO t_exposure_pathway_insights(
                    document_id, sector_id, document_name, key_word_hit_id1, key_word_hit_id2,
                    key_word1, key_word2, score, factor1, factor2, exposure_path_id, year,
                    added_dt, added_by, modify_dt, modify_by
                 ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s
                 )"""
        
        # Bulk insert
        cursor.executemany(sql, insert_data)
        timer.end_phase("database_operations")
        
        timer.start_phase("commit")
        self.dbConnection.commit()
        cursor.close()
        timer.end_phase("commit")
        
        # Enhanced metrics for bulk operations
        timer.add_metric("Insert Method", "executemany() - Bulk Insert")
        timer.add_metric("Records Prepared", len(insert_data))
        timer.add_metric("SQL Complexity", "Parameterized with 14 fields")


"""
Migration Strategy:

1. Import the new telemetry services:
   from Utilities.TelemetryServices import OperationTimer

2. Replace existing telemetry code with context manager:
   Old:
   start_time = time.time()
   # ... operation code ...
   total_time = time.time() - start_time
   self.log_generator.log_details(f"Time: {total_time}")
   
   New:
   with OperationTimer("operation_name", self.log_generator) as timer:
       timer.set_record_count(records)
       # ... operation code with timer.start_phase() / timer.end_phase()
       timer.add_metric("key", "value")

3. Benefits:
   - Automatic telemetry logging
   - Standardized output format
   - Exception handling built-in
   - Phase-level timing breakdown
   - Performance assessment
   - Reusable across all modules
"""