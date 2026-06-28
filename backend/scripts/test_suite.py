#!/usr/bin/env python3
"""
test_suite.py — Suite de tests complète pour le chatbot RAG + Prédiction
=========================================================================
Tests rapides et prêts à l'emploi pour valider :
  ✅ Retriever (KB + CSV)
  ✅ LLM Generation (Faithfulness, Relevancy)
  ✅ ML Prediction Model
  ✅ Latency & Performance
  ✅ E2E Integration

Usage:
  python test_suite.py --quick
  python test_suite.py --full
  python test_suite.py --retriever-only
"""

import json
import time
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import pickle
import pandas as pd

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

class Config:
    BACKEND_PATH = Path(__file__).parent.parent
    DJANGO_PATH = BACKEND_PATH / "django_api"
    DATA_PATH = BACKEND_PATH / "data"
    DATASET_PATH = BACKEND_PATH / "dataset"
    RESULTS_PATH = BACKEND_PATH / "results"
    MODEL_PATH = Path(__file__).parent.parent.parent / "modele-ML" / "lightgbm_shoppingclub.pkl"
    
    # SLA Thresholds
    FAITHFULNESS_MIN = 0.70
    ANSWER_RELEVANCY_MIN = 0.60
    CONTEXT_RECALL_MIN = 0.60
    PRECISION_AT_K_MIN = 0.75
    LATENCY_MAX_MS = 2000
    ACCURACY_PREDICTION_MIN = 0.70
    
    VERBOSE = False

# ═══════════════════════════════════════════════════════════════════════
# TEST UTILITIES
# ═══════════════════════════════════════════════════════════════════════

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def log_test(name: str, passed: bool, details: str = ""):
    status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"  {status} {name}")
    if details and Config.VERBOSE:
        print(f"        {Colors.BLUE}→ {details}{Colors.END}")

def log_section(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

def log_metric(name: str, value: float, threshold: float = None, unit: str = ""):
    icon = Colors.GREEN + "✅" if (threshold is None or value >= threshold) else Colors.RED + "❌"
    icon += Colors.END
    
    if threshold is not None:
        print(f"  {icon} {name:25} {value:.2%} {unit:5} (threshold: {threshold:.2%})")
    else:
        print(f"  {icon} {name:25} {value:.3f} {unit}")

# ═══════════════════════════════════════════════════════════════════════
# TEST 1 : RETRIEVER TESTS
# ═══════════════════════════════════════════════════════════════════════

class RetrieverTests:
    """Tests du module Retriever (KB + CSV)"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def test_kb_files_exist(self) -> bool:
        """Vérifie que les fichiers KB existent"""
        kb_path = Config.DATASET_PATH / "knowledge_base.json"
        exists = kb_path.exists()
        log_test("KB files exist", exists)
        
        if exists:
            with open(kb_path) as f:
                kb_data = json.load(f)
                self.passed += 1
                return len(kb_data) > 0
        
        self.failed += 1
        return False
    
    def test_csv_files_exist(self) -> bool:
        """Vérifie que les fichiers CSV existent"""
        csv_path = Config.DATA_PATH / "shoppingclub_2025_2026.csv"
        exists = csv_path.exists()
        log_test("CSV files exist", exists)
        
        if exists:
            self.passed += 1
            return True
        
        self.failed += 1
        return False
    
    def test_kb_structure(self) -> bool:
        """Vérifie la structure du KB JSON"""
        try:
            with open(Config.DATASET_PATH / "knowledge_base.json") as f:
                kb = json.load(f)
            
            # Chaque entrée doit avoir : id, title, content
            valid = all(
                isinstance(doc, dict) and all(k in doc for k in ['id', 'title', 'content'])
                for doc in kb
            )
            
            log_test("KB structure valid", valid, f"{len(kb)} docs")
            
            if valid:
                self.passed += 1
                return True
            
            self.failed += 1
            return False
        
        except Exception as e:
            log_test("KB structure valid", False, str(e))
            self.failed += 1
            return False
    
    def test_csv_structure(self) -> bool:
        """Vérifie la structure du CSV"""
        try:
            df = pd.read_csv(Config.DATA_PATH / "shoppingclub_2025_2026.csv")
            
            # Colonnes attendues
            expected_cols = {'date', 'camera', 'gender', 'age', 'hour'}
            has_cols = expected_cols.issubset(set(df.columns))
            
            log_test("CSV structure valid", has_cols, f"{len(df)} rows, {len(df.columns)} cols")
            
            if has_cols:
                self.passed += 1
                return True
            
            self.failed += 1
            return False
        
        except Exception as e:
            log_test("CSV structure valid", False, str(e))
            self.failed += 1
            return False
    
    def run_all(self) -> bool:
        """Exécute tous les tests Retriever"""
        log_section("🔍 RETRIEVER TESTS")
        
        tests = [
            self.test_kb_files_exist,
            self.test_csv_files_exist,
            self.test_kb_structure,
            self.test_csv_structure,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                log_test(test.__doc__, False, str(e))
                self.failed += 1
        
        return self.failed == 0

# ═══════════════════════════════════════════════════════════════════════
# TEST 2 : GENERATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class GenerationTests:
    """Tests du module Generation (LLM)"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def test_eval_dataset_exists(self) -> bool:
        """Vérifie que le dataset d'évaluation existe"""
        eval_path = Path(__file__).parent / "rag_eval" / "eval_dataset.json"
        exists = eval_path.exists()
        log_test("Eval dataset exists", exists)
        
        if exists:
            with open(eval_path) as f:
                dataset = json.load(f)
                log_test("Dataset has minimum 10 cases", len(dataset) >= 10, f"{len(dataset)} cases")
                self.passed += 1
                return True
        
        self.failed += 1
        return False
    
    def test_eval_dataset_structure(self) -> bool:
        """Vérifie la structure du dataset d'évaluation"""
        eval_path = Path(__file__).parent / "rag_eval" / "eval_dataset.json"
        
        try:
            with open(eval_path) as f:
                dataset = json.load(f)
            
            # Chaque cas doit avoir ces champs
            required = {'id', 'question', 'ground_truth', 'relevant_kb_ids', 'relevant_source', 'category'}
            
            valid = all(
                isinstance(case, dict) and required.issubset(set(case.keys()))
                for case in dataset
            )
            
            log_test("Dataset structure valid", valid)
            
            if valid:
                self.passed += 1
                return True
            
            self.failed += 1
            return False
        
        except Exception as e:
            log_test("Dataset structure valid", False, str(e))
            self.failed += 1
            return False
    
    def test_generation_report_exists(self) -> bool:
        """Vérifie que le rapport d'évaluation existe"""
        report_path = Config.RESULTS_PATH / "rag_eval_report.json"
        exists = report_path.exists()
        log_test("Generation report exists", exists)
        
        if exists:
            self.passed += 1
            return True
        
        print(f"        {Colors.YELLOW}→ Run: python rag_eval/evaluate_rag.py{Colors.END}")
        self.failed += 1
        return False
    
    def test_faithfulness_threshold(self) -> bool:
        """Vérifie que Faithfulness ≥ seuil"""
        report_path = Config.RESULTS_PATH / "rag_eval_report.json"
        
        if not report_path.exists():
            log_test("Faithfulness ≥ threshold", False, "Report not found")
            self.failed += 1
            return False
        
        try:
            with open(report_path) as f:
                report = json.load(f)
            
            faithfulness = report.get("generation_metrics", {}).get("faithfulness", 0)
            passes = faithfulness >= Config.FAITHFULNESS_MIN
            
            log_metric("Faithfulness", faithfulness, Config.FAITHFULNESS_MIN)
            
            if passes:
                self.passed += 1
                return True
            
            self.failed += 1
            return False
        
        except Exception as e:
            log_test("Faithfulness ≥ threshold", False, str(e))
            self.failed += 1
            return False
    
    def test_answer_relevancy_threshold(self) -> bool:
        """Vérifie que Answer Relevancy ≥ seuil"""
        report_path = Config.RESULTS_PATH / "rag_eval_report.json"
        
        if not report_path.exists():
            log_test("Answer Relevancy ≥ threshold", False, "Report not found")
            self.failed += 1
            return False
        
        try:
            with open(report_path) as f:
                report = json.load(f)
            
            relevancy = report.get("generation_metrics", {}).get("answer_relevancy", 0)
            passes = relevancy >= Config.ANSWER_RELEVANCY_MIN
            
            log_metric("Answer Relevancy", relevancy, Config.ANSWER_RELEVANCY_MIN)
            
            if passes:
                self.passed += 1
                return True
            
            self.failed += 1
            return False
        
        except Exception as e:
            log_test("Answer Relevancy ≥ threshold", False, str(e))
            self.failed += 1
            return False
    
    def run_all(self) -> bool:
        """Exécute tous les tests Generation"""
        log_section("🧠 GENERATION TESTS")
        
        tests = [
            self.test_eval_dataset_exists,
            self.test_eval_dataset_structure,
            self.test_generation_report_exists,
            self.test_faithfulness_threshold,
            self.test_answer_relevancy_threshold,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                log_test(test.__doc__, False, str(e))
                self.failed += 1
        
        return self.failed == 0

# ═══════════════════════════════════════════════════════════════════════
# TEST 3 : PREDICTION TESTS
# ═══════════════════════════════════════════════════════════════════════

class PredictionTests:
    """Tests du modèle ML de prédiction"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def test_model_file_exists(self) -> bool:
        """Vérifie que le modèle existe"""
        exists = Config.MODEL_PATH.exists()
        log_test("Model file exists", exists, str(Config.MODEL_PATH))
        
        if exists:
            self.passed += 1
            return True
        
        self.failed += 1
        return False
    
    def test_model_loadable(self) -> bool:
        """Vérifie que le modèle peut être chargé"""
        try:
            with open(Config.MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            
            has_predict = hasattr(model, 'predict')
            log_test("Model is loadable", has_predict)
            
            if has_predict:
                self.passed += 1
                return True
            
            self.failed += 1
            return False
        
        except Exception as e:
            log_test("Model is loadable", False, str(e))
            self.failed += 1
            return False
    
    def test_training_data_exists(self) -> bool:
        """Vérifie que les données d'entraînement existent"""
        csv_path = Config.DATA_PATH / "shoppingclub_2025_2026.csv"
        exists = csv_path.exists()
        log_test("Training data exists", exists)
        
        if exists:
            self.passed += 1
            return True
        
        self.failed += 1
        return False
    
    def test_model_prediction(self) -> bool:
        """Teste une prédiction simple"""
        try:
            with open(Config.MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            
            df = pd.read_csv(Config.DATA_PATH / "shoppingclub_2025_2026.csv")
            
            # Sample 10 rows
            sample = df.sample(min(10, len(df)))
            
            # Supposant que le modèle s'attend à certaines colonnes
            # (adapter selon votre modèle)
            feature_cols = [col for col in df.columns if col not in ['target', 'id', 'date']]
            
            if len(feature_cols) == 0:
                log_test("Model can make predictions", False, "No feature columns found")
                self.failed += 1
                return False
            
            X = sample[feature_cols]
            predictions = model.predict(X)
            
            valid = len(predictions) == len(X)
            log_test("Model can make predictions", valid, f"{len(predictions)} predictions")
            
            if valid:
                self.passed += 1
                return True
            
            self.failed += 1
            return False
        
        except Exception as e:
            log_test("Model can make predictions", False, str(e))
            self.failed += 1
            return False
    
    def run_all(self) -> bool:
        """Exécute tous les tests Prediction"""
        log_section("🤖 PREDICTION MODEL TESTS")
        
        tests = [
            self.test_model_file_exists,
            self.test_model_loadable,
            self.test_training_data_exists,
            self.test_model_prediction,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                log_test(test.__doc__, False, str(e))
                self.failed += 1
        
        return self.failed == 0

# ═══════════════════════════════════════════════════════════════════════
# TEST 4 : PERFORMANCE TESTS
# ═══════════════════════════════════════════════════════════════════════

class PerformanceTests:
    """Tests de performance (latence, débit, etc)"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
    
    def test_eval_report_latency(self) -> bool:
        """Vérifie les latences dans le rapport d'évaluation"""
        report_path = Config.RESULTS_PATH / "rag_eval_report.json"
        
        if not report_path.exists():
            log_test("Latency metrics available", False, "Report not found")
            self.failed += 1
            return False
        
        try:
            with open(report_path) as f:
                report = json.load(f)
            
            avg_latency = report.get("summary", {}).get("avg_latency_ms", 0)
            
            if avg_latency > 0:
                passes = avg_latency < Config.LATENCY_MAX_MS
                log_metric("Avg Latency", avg_latency / 1000, None, "seconds")
                
                if passes:
                    self.passed += 1
                    return True
                
                self.failed += 1
                return False
            
            self.failed += 1
            return False
        
        except Exception as e:
            log_test("Latency metrics available", False, str(e))
            self.failed += 1
            return False
    
    def run_all(self) -> bool:
        """Exécute tous les tests de performance"""
        log_section("⚡ PERFORMANCE TESTS")
        
        tests = [
            self.test_eval_report_latency,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                log_test(test.__doc__, False, str(e))
                self.failed += 1
        
        return self.failed == 0

# ═══════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════

class TestRunner:
    """Orchestrateur principal des tests"""
    
    def __init__(self):
        self.retriever_tests = RetrieverTests()
        self.generation_tests = GenerationTests()
        self.prediction_tests = PredictionTests()
        self.performance_tests = PerformanceTests()
    
    def run_quick(self) -> bool:
        """Tests rapides (fichiers, structure)"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}QUICK TEST SUITE{Colors.END}\n")
        
        results = [
            self.retriever_tests.run_all(),
            self.generation_tests.run_all(),
            self.prediction_tests.run_all(),
        ]
        
        return all(results)
    
    def run_full(self) -> bool:
        """Suite complète de tests"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}FULL TEST SUITE{Colors.END}\n")
        
        results = [
            self.retriever_tests.run_all(),
            self.generation_tests.run_all(),
            self.prediction_tests.run_all(),
            self.performance_tests.run_all(),
        ]
        
        return all(results)
    
    def run_retriever_only(self) -> bool:
        """Tests Retriever uniquement"""
        return self.retriever_tests.run_all()
    
    def print_summary(self, passed: bool):
        """Affiche un résumé final"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        
        if passed:
            print(f"{Colors.BOLD}{Colors.GREEN}✅ ALL TESTS PASSED{Colors.END}")
            print(f"\nNext steps:")
            print(f"  1. Run the full RAG evaluation:")
            print(f"     {Colors.YELLOW}cd backend/scripts && python rag_eval/evaluate_rag.py{Colors.END}")
            print(f"  2. Check the report:")
            print(f"     {Colors.YELLOW}cat backend/results/rag_eval_report.json{Colors.END}")
            print(f"  3. Monitor metrics:")
            print(f"     {Colors.YELLOW}python metrics_dashboard.py{Colors.END}")
        else:
            print(f"{Colors.BOLD}{Colors.RED}❌ SOME TESTS FAILED{Colors.END}")
            print(f"\nActions:")
            print(f"  1. Check the errors above")
            print(f"  2. Run with --verbose for more details:")
            print(f"     {Colors.YELLOW}python test_suite.py --full --verbose{Colors.END}")
        
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Test suite for RAG + Prediction pipeline"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Run quick tests (files, structure) [default]"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Run full test suite (includes performance)"
    )
    parser.add_argument(
        "--retriever-only", action="store_true",
        help="Run only Retriever tests"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    Config.VERBOSE = args.verbose
    
    runner = TestRunner()
    
    if args.full:
        passed = runner.run_full()
    elif args.retriever_only:
        passed = runner.run_retriever_only()
    else:
        passed = runner.run_quick()
    
    runner.print_summary(passed)
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()