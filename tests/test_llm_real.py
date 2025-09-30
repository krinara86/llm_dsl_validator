# test_llm_real.py
"""
Real LLM integration tests - not run by default.
Run with: pytest tests/test_llm_real.py -m llm_tests
"""

import pytest
import json
import time
from pathlib import Path
import sys
from typing import Dict, List, Tuple
from collections import Counter
import statistics

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from src.conversation.extractor import TaskExtractor
from src.conversation.document_processor import DocumentProcessor
from src.core.llm_client import LLMClient
from test_fixtures import EVENT_CONNECTOR

# Mark all tests in this file as llm_tests
pytestmark = pytest.mark.llm_tests


def check_llm_available(model_name: str = "llama3:8b") -> bool:
    """Check if LLM is available."""
    try:
        import requests
        if model_name.startswith("llama"):
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        return True  # Assume cloud models are available if API key exists
    except:
        return False


@pytest.mark.skipif(not check_llm_available(), reason="LLM not available")
class TestLLMExtraction:
    """Test actual LLM extraction with multiple runs and statistical validation."""
    
    def setup_method(self):
        """Set up test parameters."""
        self.extractor = TaskExtractor()
        self.model = "llama3:8b"  # Change to your preferred model
        self.num_runs = 3  # Number of times to run each test
        self.success_threshold = 0.66  # 2 out of 3 should pass
    
    def run_multiple_times(self, query: str, validation_func) -> Tuple[float, List[Dict]]:
        """Run extraction multiple times and calculate success rate."""
        results = []
        successes = 0
        
        for i in range(self.num_runs):
            try:
                result = self.extractor.extract_task_details(query, self.model, EVENT_CONNECTOR)
                results.append(result)
                if validation_func(result):
                    successes += 1
                time.sleep(0.1)  # Small delay between requests
            except Exception as e:
                results.append({"error": str(e)})
        
        success_rate = successes / self.num_runs
        return success_rate, results
    
    @pytest.mark.slow
    def test_simple_create_extraction_consistency(self):
        """Test if simple create commands are consistently extracted."""
        query = "Create a venue called Conference Hall"
        
        def validate(result):
            return (result.get("action") == "create_venue" and 
                   "Conference Hall" in str(result.get("parameters", {}).get("name", "")))
        
        success_rate, results = self.run_multiple_times(query, validate)
        
        print(f"\n[Simple Create] Success rate: {success_rate:.1%}")
        print(f"Results: {json.dumps(results, indent=2)}")
        
        assert success_rate >= self.success_threshold, \
               f"Success rate {success_rate:.1%} below threshold {self.success_threshold:.1%}"
    
    @pytest.mark.slow
    def test_numeric_extraction_accuracy(self):
        """Test if numeric values are extracted accurately."""
        queries_and_expected = [
            ("Create Meeting Room with 25 seats", 25),
            ("Book Conference Hall for 100 people", 100),
            ("Create Auditorium with capacity of 500", 500)
        ]
        
        all_success_rates = []
        
        for query, expected_num in queries_and_expected:
            def validate(result):
                params = result.get("parameters", {})
                # Check various possible parameter names
                for key in ["capacity", "expected_attendees", "seats"]:
                    if key in params:
                        try:
                            return abs(int(params[key]) - expected_num) <= 5  # Allow small variance
                        except:
                            pass
                return False
            
            success_rate, results = self.run_multiple_times(query, validate)
            all_success_rates.append(success_rate)
            print(f"\n[Numeric: {expected_num}] Success rate: {success_rate:.1%}")
        
        avg_success = statistics.mean(all_success_rates)
        assert avg_success >= self.success_threshold, \
               f"Average success rate {avg_success:.1%} below threshold"
    
    @pytest.mark.slow
    def test_boolean_extraction_patterns(self):
        """Test different patterns for boolean extraction."""
        true_patterns = [
            "Book room with AV equipment",
            "Create venue that has AV system",
            "Reserve space with audio visual"
        ]
        
        false_patterns = [
            "Book room without AV equipment",
            "Create venue with no AV system",
            "Reserve space, no audio visual needed"
        ]
        
        def test_patterns(patterns, expected_value):
            success_rates = []
            for pattern in patterns:
                def validate(result):
                    params = result.get("parameters", {})
                    for key in ["requires_av", "has_av_system"]:
                        if key in params:
                            return params[key] == expected_value
                    return False
                
                success_rate, _ = self.run_multiple_times(pattern, validate)
                success_rates.append(success_rate)
            
            return statistics.mean(success_rates)
        
        true_success = test_patterns(true_patterns, True)
        false_success = test_patterns(false_patterns, False)
        
        print(f"\n[Boolean True patterns] Average success: {true_success:.1%}")
        print(f"[Boolean False patterns] Average success: {false_success:.1%}")
        
        assert true_success >= 0.5, "True patterns not recognized reliably"
        assert false_success >= 0.5, "False patterns not recognized reliably"


@pytest.mark.skipif(not check_llm_available(), reason="LLM not available")
class TestLLMRobustness:
    """Test LLM robustness with edge cases and variations."""
    
    def setup_method(self):
        """Set up test parameters."""
        self.extractor = TaskExtractor()
        self.model = "llama3:8b"
    
    @pytest.mark.slow
    def test_typo_tolerance(self):
        """Test if LLM handles minor typos."""
        queries_with_typos = [
            "Crate a venue called Main Hall",  # Create → Crate
            "Book Confrence Room for 30 people",  # Conference → Confrence
            "Create vanue with 50 seats"  # venue → vanue
        ]
        
        successes = 0
        for query in queries_with_typos:
            try:
                result = self.extractor.extract_task_details(query, self.model, EVENT_CONNECTOR)
                # Just check if it extracts a valid action (not "unknown")
                if result.get("action") not in [None, "unknown", "error"]:
                    successes += 1
            except:
                pass
        
        success_rate = successes / len(queries_with_typos)
        print(f"\n[Typo Tolerance] Success rate: {success_rate:.1%}")
        
        assert success_rate >= 0.5, "LLM should handle at least half of typos"
    
    @pytest.mark.slow
    def test_paraphrase_invariance(self):
        """Test if different phrasings yield similar results."""
        paraphrase_groups = [
            [
                "Create a room called Board Room",
                "Make a new room named Board Room",
                "Add a room with the name Board Room",
                "Set up Board Room as a new venue"
            ],
            [
                "Book the hall for 50 people",
                "Reserve the hall for 50 attendees",
                "Schedule the hall for a group of 50",
                "Need the hall for 50 participants"
            ]
        ]
        
        for group in paraphrase_groups:
            actions = []
            for query in group:
                try:
                    result = self.extractor.extract_task_details(query, self.model, EVENT_CONNECTOR)
                    actions.append(result.get("action"))
                except:
                    actions.append("error")
            
            # Check if most extractions got the same action
            most_common = Counter(actions).most_common(1)[0]
            consistency_rate = most_common[1] / len(actions)
            
            print(f"\n[Paraphrase Group] Most common action: {most_common[0]}")
            print(f"Consistency: {consistency_rate:.1%} ({most_common[1]}/{len(actions)})")
            
            assert consistency_rate >= 0.5, "Paraphrases should yield consistent actions"


@pytest.mark.skipif(not check_llm_available(), reason="LLM not available")
class TestLLMDocumentProcessing:
    """Test document processing with real LLM."""
    
    def setup_method(self):
        """Set up test parameters."""
        self.processor = DocumentProcessor()
        self.model = "llama3:8b"
    
    @pytest.mark.slow
    def test_multi_task_separation(self):
        """Test if LLM correctly separates multiple tasks."""
        documents = [
            "Create Room A with 30 seats. Create Room B with 20 seats.",
            "First, create Conference Hall. Then book it for 50 people.",
            "Register these venues: Main Hall, Board Room, Training Room"
        ]
        
        expected_counts = [2, 2, 3]
        
        for doc, expected in zip(documents, expected_counts):
            result = self.processor.extract_tasks(doc, self.model, EVENT_CONNECTOR)
            
            task_count = len(result.get("tasks", []))
            print(f"\n[Multi-task] Expected: {expected}, Got: {task_count}")
            print(f"Document: {doc[:50]}...")
            
            # Allow ±1 task difference
            assert abs(task_count - expected) <= 1, \
                   f"Expected {expected}±1 tasks, got {task_count}"
    
    @pytest.mark.slow  
    def test_entity_property_grouping(self):
        """Test if properties stay with their entities."""
        doc = "Create Auditorium with 500 capacity, AV system, and wheelchair access"
        
        result = self.processor.extract_tasks(doc, self.model, EVENT_CONNECTOR)
        
        assert len(result.get("tasks", [])) == 1, "Should be ONE task with multiple properties"
        
        if result.get("tasks"):
            task = result["tasks"][0]
            details = task.get("details", {})
            
            # Check if at least the name and capacity made it through
            has_name = "Auditorium" in str(details.get("name", ""))
            has_capacity = any(k in details for k in ["capacity", "seats"])
            
            print(f"\n[Property Grouping] Has name: {has_name}, Has capacity: {has_capacity}")
            print(f"Details extracted: {details}")
            
            assert has_name, "Should preserve entity name"


class TestLLMPerformanceMetrics:
    """Measure LLM performance metrics."""
    
    def setup_method(self):
        """Set up test parameters."""
        self.extractor = TaskExtractor()
        self.model = "llama3:8b"
    
    @pytest.mark.slow
    @pytest.mark.benchmark
    def test_response_time_distribution(self):
        """Measure response time distribution."""
        queries = [
            "Create room",  # Very simple
            "Create Conference Room with 50 seats",  # Medium
            "Create Auditorium with 200 capacity, AV system, recording equipment, and live streaming"  # Complex
        ]
        
        for query in queries:
            times = []
            for _ in range(5):
                start = time.time()
                try:
                    self.extractor.extract_task_details(query, self.model, EVENT_CONNECTOR)
                    elapsed = time.time() - start
                    times.append(elapsed)
                except:
                    pass
            
            if times:
                avg_time = statistics.mean(times)
                median_time = statistics.median(times)
                std_dev = statistics.stdev(times) if len(times) > 1 else 0
                
                print(f"\n[Performance: {len(query)} chars]")
                print(f"  Average: {avg_time:.2f}s")
                print(f"  Median: {median_time:.2f}s")
                print(f"  Std Dev: {std_dev:.2f}s")
                
                # Basic performance assertion
                assert median_time < 5.0, f"Median response time {median_time:.2f}s exceeds 5s limit"


# Fixture to print test configuration
@pytest.fixture(scope="session", autouse=True)
def print_llm_test_config():
    """Print LLM test configuration."""
    print("\n" + "="*60)
    print("LLM INTEGRATION TESTS")
    print("="*60)
    print("These tests use real LLM calls and may be non-deterministic.")
    print("Results may vary based on model, temperature, and other factors.")
    print("="*60 + "\n")
    yield
    print("\n" + "="*60)
    print("LLM tests completed")
    print("="*60)