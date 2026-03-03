export interface ModuleDTO {
  file_path: string;
  function_count: number;
  class_count: number;
  endpoint_count: number;
}

export interface AnalysisDTO {
  id: string;
  root_path: string;
  modules: ModuleDTO[];
  languages: string[];
  total_functions: number;
  total_classes: number;
  total_modules: number;
}

export interface TestCaseDTO {
  name: string;
  description: string;
  layer: string;
  target_function: string;
  target_module: string;
  priority: number;
}

export interface TestSuiteDTO {
  layer: string;
  test_cases: TestCaseDTO[];
  size: number;
}

export interface StrategyDTO {
  id: string;
  analysis_id: string;
  suites: TestSuiteDTO[];
  total_test_cases: number;
  layers_covered: string[];
}

export interface GeneratedSuite {
  layer: string;
  size: number;
  output_dir: string;
}

export interface TestResult {
  name: string;
  outcome: string;
  duration: number | null;
  message: string | null;
}

export interface ExecutionResults {
  total: number;
  passed: number;
  failed: number;
  errors: number;
  skipped: number;
  success_rate: number;
  tests: TestResult[];
}

export interface GapModule {
  file_path: string;
  tested: string[];
  untested: string[];
  tested_count: number;
  total_count: number;
}

export interface GapsReport {
  coverage_percent: number;
  tested: number;
  total: number;
  untested_count: number;
  untested: string[];
  modules: GapModule[];
}

export interface ValidationResult {
  file_path: string;
  valid: boolean;
  errors: string[];
}

export interface ValidationReport {
  total: number;
  passed: number;
  failed: number;
  success_rate: number;
  results: ValidationResult[];
}

export interface RepairResult {
  file: string;
  success: boolean;
  attempt: number;
  error: string | null;
}

export interface RepairReport {
  fixed: number;
  total: number;
  results: RepairResult[];
  message?: string;
}

export interface MutantSurvivor {
  id: string;
  source_file: string;
}

export interface MutationReport {
  mutation_score: number;
  total: number;
  killed: number;
  survived: number;
  timeout: number;
  survivors: MutantSurvivor[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolCalls?: { name: string; result: string }[];
}
