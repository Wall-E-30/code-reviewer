---
phase: 05-model-training
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - rl/training/__init__.py
  - rl/training/config.py
  - rl/training/formatter.py
  - rl/training/sft.py
  - tests/test_sft_pipeline.py
autonomous: true
requirements:
  - TRAIN-01
must_haves:
  truths:
    - Training episodes from data/episodes/ are converted into ChatML instruction-tuning format with diff context, modified file content, repo conventions, and structured JSON outputs.
    - Clean diff negative episodes are explicitly formatted to teach the model to emit empty reviews ({"comments": []}) with zero hallucinations.
    - SFT training pipeline supports QLoRA 4-bit / PEFT on open code models (e.g. Qwen2.5-Coder) and features a dry-run / CPU mode for fast execution in CI environments.
    - Format adherence and initial diff comprehension evaluation functions verify that output comments contain valid line numbers, categories, concise explanations, and syntax-valid suggestions.
  artifacts:
    - rl/training/config.py
    - rl/training/formatter.py
    - rl/training/sft.py
    - tests/test_sft_pipeline.py
  key_links:
    - rl/training/formatter.py consumes data/episodes/episodes_stream.jsonl generated in Phase 4.
    - rl/training/sft.py produces warm-start model checkpoints used as the reference policy for GRPO in Plan 05-03.
---

<objective>
Build the SFT (Supervised Fine-Tuning) warm-start pipeline and dataset formatting engine for open code models (e.g. Qwen2.5-Coder 1.5B/7B).
Transform the 10,000 verified training episodes into ChatML instruction tuning format, establish QLoRA/PEFT training scripts with free GPU / CPU dry-run compatibility, and evaluate initial diff comprehension and format adherence.

Purpose: Provide the warm-start policy foundation that teaches the base code model how to read unified git diffs, respect repository conventions, and emit structured inline reviews with valid GitHub suggestions before RL fine-tuning.
Output: `rl/training/config.py`, `rl/training/formatter.py`, `rl/training/sft.py`, and `tests/test_sft_pipeline.py`.
</objective>

<execution_context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-model-training/RESEARCH.md
@data/episodes/training_manifest.json
@rl/env.py
@bench/schema.py
</execution_context>

<tasks>

<task type="tracer">
  <name>Implement Training Configuration and ChatML Dataset Formatter</name>
  <files>rl/training/__init__.py, rl/training/config.py, rl/training/formatter.py</files>
  <action>
1. Create `rl/training/__init__.py`.
2. In `rl/training/config.py`:
   - Implement `TrainingConfig` dataclass:
     - Model selection: `base_model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"` (with optional `"Qwen/Qwen2.5-Coder-7B-Instruct"`).
     - QLoRA params: `lora_r: int = 16`, `lora_alpha: int = 32`, `lora_dropout: float = 0.05`, `target_modules: List[str]`.
     - Hyperparameters: `learning_rate: float = 2e-4`, `batch_size: int = 4`, `gradient_accumulation_steps: int = 4`, `max_seq_length: int = 2048`, `num_train_epochs: int = 3`, `warmup_ratio: float = 0.05`.
     - Hardware & Execution profile: `device: str = "auto"`, `fp16: bool = True`, `dry_run: bool = False`, `max_samples: Optional[int] = None`.
3. In `rl/training/formatter.py`:
   - Implement `ChatMLFormatter`:
     - `format_episode(episode_dict: Dict[str, Any]) -> Dict[str, Any]`:
       - System prompt: Role definition as expert code reviewer adhering to strict precision and format constraints.
       - User prompt: Injects `active_conventions`, file path, programming language, unified `diff`, and `file_content`.
       - Assistant response: Structured JSON with `"comments": [...]`.
       - If `is_clean_diff` is True or ground-truth is empty: Assistant response must be `{"comments": []}` (critical negative control).
       - For injected/replay cases with findings: Assistant response serializes line numbers, category, explanation, and `suggestion` block.
     - `convert_stream_to_sft_jsonl(input_jsonl_path: str, output_jsonl_path: str, max_records: Optional[int] = None) -> int`:
       - Streams episodes from `data/episodes/episodes_stream.jsonl`, formats them, and writes standardized instruction records.
       - Returns total count of converted training instances.
  </action>
  <verify>
python -c "from rl.training.formatter import ChatMLFormatter; f = ChatMLFormatter(); ep = {'case_id': 'test-1', 'language': 'python', 'file_path': 'test.py', 'diff': '@@ -1 +1 @@\n-a\n+b\n', 'file_content': 'b = 1\n', 'is_clean_diff': True, 'ground_truth': [], 'active_conventions': []}; res = f.format_episode(ep); assert 'messages' in res and '{\"comments\": []}' in res['messages'][-1]['content']; print('Formatter tracer verified')"
  </verify>
</task>

<task>
  <name>Implement SFT Training Pipeline with QLoRA and CPU Dry-Run Support</name>
  <files>rl/training/sft.py</files>
  <action>
1. In `rl/training/sft.py`:
   - Implement `SFTWarmStartTrainer`:
     - Constructor accepting `TrainingConfig`.
     - `prepare_dataset(jsonl_path: str) -> Any`: Loads and tokenizes formatted ChatML dataset.
     - `setup_model_and_tokenizer()`:
       - If CUDA is available and not `dry_run`: Configures `BitsAndBytesConfig` (4-bit quantization, NF4, double quant) and initializes `peft.LoraConfig`.
       - If CUDA is not available or `dry_run`: Fallback to lean CPU model execution or synthetic mock parameter updates ensuring zero CI environment crashes.
     - `train(train_dataset_path: str, output_dir: str) -> Dict[str, Any]`:
       - Executes training loop (or fast CPU simulation if `dry_run=True`), logging train loss, token accuracy, and training wall-clock time.
       - Saves adapter weights and tokenizer configuration to `output_dir`.
       - Returns training summary metrics dict.
     - `evaluate_diff_comprehension(model, tokenizer, test_cases: List[Dict[str, Any]]) -> Dict[str, float]`:
       - Tests format adherence: checks that generated completions are valid JSON containing line numbers and valid syntax suggestions.
       - Computes format validity rate ($\ge 95\%$) and clean-diff compliance rate.
  </action>
  <verify>
python -c "from rl.training.config import TrainingConfig; from rl.training.sft import SFTWarmStartTrainer; cfg = TrainingConfig(dry_run=True, max_samples=5); trainer = SFTWarmStartTrainer(cfg); res = trainer.train('data/episodes/episodes_stream.jsonl', 'models/test_sft_out'); assert 'train_loss' in res; print('SFT pipeline dry-run verified')"
  </verify>
</task>

<task>
  <name>Build SFT Pipeline Unit and Integration Test Suite</name>
  <files>tests/test_sft_pipeline.py</files>
  <action>
1. In `tests/test_sft_pipeline.py`, write comprehensive test cases:
   - `test_chatml_formatting_clean_diff()`: Confirms clean diff yields empty comments array.
   - `test_chatml_formatting_bug_injection()`: Confirms injected bug preserves line anchor, category, and code replacement.
   - `test_stream_conversion_sample()`: Converts small slice of `data/episodes/episodes_stream.jsonl` and validates output JSONL schema.
   - `test_sft_config_defaults()`: Checks hyperparameter defaults (learning rate, LoRA rank, warmup).
   - `test_sft_dry_run_training_execution()`: Executes `SFTWarmStartTrainer` in `dry_run=True` mode, verifies artifact creation and return metrics.
   - `test_diff_comprehension_format_adherence()`: Verifies evaluation metric checks JSON validity and suggestion syntax.
  </action>
  <verify>
python -m pytest tests/test_sft_pipeline.py -v
  </verify>
</task>

</tasks>

