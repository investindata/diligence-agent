#!/usr/bin/env python3
"""
Script to test the corrected cost calculation and show the exact fix needed.
"""

def current_wrong_calculation(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Current wrong method from utils.py"""
    # Wrong pricing - rates are per 1M tokens but we divide by 1K
    pricing = {
        'gpt-4.1-mini': {'prompt': 0.00015, 'completion': 0.0006}  # per 1M tokens
    }

    model_pricing = pricing.get('gpt-4.1-mini', {'prompt': 0.00015, 'completion': 0.0006})

    # ❌ WRONG: Dividing by 1000 but rates are per 1M
    prompt_cost = (prompt_tokens / 1000) * model_pricing['prompt']
    completion_cost = (completion_tokens / 1000) * model_pricing['completion']

    return prompt_cost + completion_cost

def corrected_calculation(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Corrected method"""
    # Correct pricing - rates per 1M tokens
    pricing = {
        'gpt-4.1-mini': {'prompt': 0.15, 'completion': 0.60}  # per 1M tokens ($ amounts)
    }

    model_pricing = pricing.get('gpt-4.1-mini', {'prompt': 0.15, 'completion': 0.60})

    # ✅ CORRECT: Dividing by 1M for rates per 1M tokens
    prompt_cost = (prompt_tokens / 1_000_000) * model_pricing['prompt']
    completion_cost = (completion_tokens / 1_000_000) * model_pricing['completion']

    return prompt_cost + completion_cost

def test_fix():
    """Test the fix with real usage data"""

    # Real usage from your screenshot
    test_case = {
        "model": "gpt-4.1-mini",
        "prompt_tokens": 2569,
        "completion_tokens": 264
    }

    print("=" * 80)
    print("COST CALCULATION FIX TEST")
    print("=" * 80)
    print(f"Model: {test_case['model']}")
    print(f"Prompt tokens: {test_case['prompt_tokens']:,}")
    print(f"Completion tokens: {test_case['completion_tokens']:,}")
    print()

    # Current wrong calculation
    wrong_cost = current_wrong_calculation(
        test_case['model'],
        test_case['prompt_tokens'],
        test_case['completion_tokens']
    )

    # Corrected calculation
    correct_cost = corrected_calculation(
        test_case['model'],
        test_case['prompt_tokens'],
        test_case['completion_tokens']
    )

    print("💰 Cost Comparison:")
    print(f"  Current (WRONG): ${wrong_cost:.6f}")
    print(f"  Corrected:       ${correct_cost:.6f}")
    print(f"  Overcharge by:   {wrong_cost/correct_cost:.1f}x")
    print()

    print("🔧 Required Fix in utils.py:")
    print("  Change line ~122-123 from:")
    print("    prompt_cost = (prompt_tokens / 1000) * model_pricing['prompt']")
    print("    completion_cost = (completion_tokens / 1000) * model_pricing['completion']")
    print("  To:")
    print("    prompt_cost = (prompt_tokens / 1_000_000) * model_pricing['prompt']")
    print("    completion_cost = (completion_tokens / 1_000_000) * model_pricing['completion']")
    print()

    print("🔧 And update the pricing rates from:")
    print("    'gpt-4.1-mini': {'prompt': 0.00015, 'completion': 0.0006}")
    print("  To:")
    print("    'gpt-4.1-mini': {'prompt': 0.15, 'completion': 0.60}")
    print()

    # Breakdown
    print("🧮 Detailed Breakdown (Corrected):")
    input_cost = (test_case['prompt_tokens'] / 1_000_000) * 0.15
    output_cost = (test_case['completion_tokens'] / 1_000_000) * 0.60
    print(f"  Input:  {test_case['prompt_tokens']:,} tokens × $0.15/1M = ${input_cost:.6f}")
    print(f"  Output: {test_case['completion_tokens']:,} tokens × $0.60/1M = ${output_cost:.6f}")
    print(f"  Total:  ${input_cost + output_cost:.6f}")

if __name__ == "__main__":
    test_fix()