# Qwen2.5-Coder-7B precision comparison on HumanEval-164

## Result

On the complete 164-problem HumanEval benchmark, the local Q4_K_M run solved
136 problems (`pass@1_single = 136/164 = 0.8293`) and the full-precision
(`bfloat16`) cluster run solved 142 (`142/164 = 0.8659`). The observed
difference is **+6 net problems, or +3.66 percentage points** (3.6585 points
before rounding; approximately 3.65 points). Ten problem outcomes changed: the
full-precision run recovered eight Q4 failures and lost two Q4 successes.

This is the dissertation-relevant operational finding: the 4-bit local
development configuration has a measurable approximately 3.65-point accuracy
gap relative to the full-precision reporting configuration on this
benchmark/model. Local development results throughout the project should
therefore be treated as directionally indicative, not capability-precise;
headline dissertation claims must use the full-precision cluster results.

There is one important causal qualification. The comparison configurations
also necessarily changed inference backend and hardware (Ollama on CPU versus
Hugging Face on CUDA), and HumanEval/39 changed outcome because `sympy` was
absent from the local execution environment, despite effectively identical
generated code. Thus, **3.66 points is the observed end-to-end configuration
gap, not a clean causal estimate of weight quantization alone**. Nine flips
were generation changes consistent with precision/backend sensitivity; after
excluding the environment-only HumanEval/39 flip, the net generation-related
gap is +5/164 = 3.05 percentage points. A strictly causal quantization estimate
would require the same inference and execution stacks with only weight dtype
changed.

## Methodology and controls

The paired runs were:

- Q4_K_M: [`20260715T215247Z_m7_quantized_local_development_single_humaneval_full`](../../experiments/results/20260715T215247Z_m7_quantized_local_development_single_humaneval_full/)
- Full precision: [`20260808T204450.467851Z_cluster_qwen_hf_zero_shot_humaneval_full`](../../experiments/results/20260808T204450.467851Z_cluster_qwen_hf_zero_shot_humaneval_full/)

The comparison held fixed the canonical model
`Qwen/Qwen2.5-Coder-7B-Instruct`, Hugging Face revision
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, complete 164-task dataset and
source URL, task order, zero-shot prompt strategy, system and user prompts,
seed 42, temperature 0.2, top-p 0.95, maximum 512 new tokens, repetition
penalty 1.1, subprocess executor, 10-second timeout, and 512 MiB memory limit.
Artifact audit confirmed identical task IDs, rendered system prompts, rendered
user prompts, and test cases for all 164 pairs. Both runs used their committed
config snapshots and recorded the generation seed in `seeds.json`.

The intended treatment was model precision: the local artifact was Ollama
`qwen2.5-coder:7b-instruct-q4_K_M` (digest
`dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`),
whereas the cluster loaded the pinned model revision through Hugging Face as
`torch.bfloat16` without quantization. These distinct representations required
different backends and devices, so identical random seed means matched run
configuration and reproducibility metadata, not guaranteed token-for-token
sampling equivalence across implementations. The execution dependency
difference exposed by HumanEval/39 is recorded rather than silently assigned
to quantization.

## Outcome flips

| Problem | Q4_K_M | Full precision | Direction | One-line code-level explanation |
|---|---:|---:|---|---|
| HumanEval/39 | Fail | Pass | Recovered | Generated logic was effectively identical; only Q4 failed because its sandbox lacked the imported `sympy`, so this is an environment flip. |
| HumanEval/46 | Fail | Pass | Recovered | Full precision starts the four-term recurrence loop at 4 instead of 3, fixing the one-step offset. |
| HumanEval/93 | Fail | Pass | Recovered | Full precision swaps case before applying the two-letter vowel shift; Q4 shifted vowels without performing the required case swap. |
| HumanEval/99 | Fail | Pass | Recovered | Full precision uses floor/ceiling half-away-from-zero rounding, correctly handling negative `.5` ties. |
| HumanEval/113 | Fail | Pass | Recovered | Full precision interpolates the odd-digit count; Q4 used `s.index(s)+1`, which produced the list position (and was always 1 for the current string). |
| HumanEval/121 | Fail | Pass | Recovered | Full precision sums odd values at zero-based even indices; Q4 selected odd indices. |
| HumanEval/125 | Fail | Pass | Recovered | Full precision counts lowercase letters at odd alphabet offsets, correcting Q4's reversed parity test. |
| HumanEval/146 | Fail | Pass | Recovered | Full precision checks only the first and last digits for oddness; Q4 incorrectly required every digit to be odd. |
| HumanEval/141 | Pass | Fail | Lost | Full precision replaced direct structural checks with a regex that overconstrains digit placement to one contiguous block. |
| HumanEval/155 | Pass | Fail | Lost | Full precision's arithmetic loop skips zero entirely, while Q4's string traversal correctly counts the digit `0` as even. |

The eight recoveries and two losses give the observed net change of +6.

## Generated-code audit

The following is the exact extracted `generation.code` from each committed
per-problem JSON record. Whitespace differences are retained.

### HumanEval/39 — recovered (execution-environment difference)

Q4_K_M:

```python
from sympy import isprime

def prime_fib(n: int) -> int:
    def fib_generator():
        a, b = 0, 1
        while True:
            yield b
            a, b = b, a + b

    count = 0
    for fib_num in fib_generator():
        if fib_num > 1 and isprime(fib_num):
            count += 1
            if count == n:
                return fib_num
```

Full precision:

```python
from sympy import isprime

def prime_fib(n: int) -> int:
    def fib_generator():
        a, b = 0, 1
        while True:
            yield b
            a, b = b, a + b
    
    count = 0
    for fib_num in fib_generator():
        if fib_num > 1 and isprime(fib_num):
            count += 1
            if count == n:
                return fib_num
```

The only code difference is whitespace. Q4 raised
`ModuleNotFoundError: No module named 'sympy'`; full precision passed with the
same import available.

### HumanEval/46 — recovered (recurrence boundary)

Q4_K_M:

```python
def fib4(n: int) -> int:
    if n < 2:
        return 0
    elif n == 2:
        return 2
    else:
        a, b, c, d = 0, 0, 2, 0
        for _ in range(3, n + 1):
            a, b, c, d = b, c, d, a + b + c + d
        return d
```

Full precision:

```python
def fib4(n: int) -> int:
    if n < 2:
        return 0
    elif n == 2:
        return 2
    else:
        a, b, c, d = 0, 0, 2, 0
        for _ in range(4, n + 1):
            a, b, c, d = b, c, d, a + b + c + d
        return d
```

### HumanEval/93 — recovered (case transformation order)

Q4_K_M:

```python
def encode(message):
    vowels = "aeiou"
    shifted_vowels = {v: chr((ord(v) - 97 + 2) % 26 + 97) for v in vowels}
    shifted_vowels.update({v.upper(): shifted_vowels[v].upper() for v in vowels})
    
    encoded_message = []
    for char in message:
        if char.isalpha():
            if char.lower() in vowels:
                encoded_char = shifted_vowels[char]
            else:
                encoded_char = char.swapcase()
            encoded_message.append(encoded_char)
        else:
            encoded_message.append(char)
    
    return ''.join(encoded_message)
```

Full precision:

```python
def encode(message):
    vowels = "aeiou"
    shifted_vowels = {v: chr((ord(v) - ord('a') + 2) % 26 + ord('a')) for v in vowels}
    shifted_vowels.update({v.upper(): shifted_vowels[v].upper() for v in vowels})
    
    encoded_message = []
    for char in message:
        if char.isalpha():
            if char.islower():
                new_char = char.upper()
            else:
                new_char = char.lower()
            
            if new_char in shifted_vowels:
                new_char = shifted_vowels[new_char]
            
            encoded_message.append(new_char)
        else:
            encoded_message.append(char)
    
    return ''.join(encoded_message)
```

### HumanEval/99 — recovered (negative half ties)

Q4_K_M:

```python
def closest_integer(value):
    num = float(value)
    if abs(num - round(num)) == 0.5:
        return int(num + (num > 0))
    else:
        return round(num)
```

Full precision:

```python
import math

def closest_integer(value):
    num = float(value)
    if num > 0:
        return math.floor(num + 0.5)
    else:
        return math.ceil(num - 0.5)
```

### HumanEval/113 — recovered (wrong interpolated quantity)

Q4_K_M:

```python
def odd_count(lst):
    return [f"the number of odd elements {sum(1 for char in s if int(char) % 2 != 0)}n the str{s.index(s)+1}ng {s.index(s)+1} of the {s.index(s)+1}nput." for s in lst]
```

Full precision:

```python
def odd_count(lst):
    result = []
    for s in lst:
        num_odds = sum(1 for char in s if int(char) % 2 == 1)
        result.append(f"the number of odd elements {num_odds}n the str{num_odds}ng {num_odds} of the {num_odds}nput.")
    return result
```

### HumanEval/121 — recovered (index parity)

Q4_K_M:

```python
def solution(lst):
    return sum(x for i, x in enumerate(lst) if i % 2 == 1 and x % 2 == 1)
```

Full precision:

```python
def solution(lst):
    return sum(x for i, x in enumerate(lst) if i % 2 == 0 and x % 2 != 0)
```

### HumanEval/125 — recovered (alphabet-index parity)

Q4_K_M:

```python
def split_words(txt):
    if ' ' in txt:
        return txt.split()
    elif ',' in txt:
        return txt.split(',')
    else:
        return sum(1 for char in txt if char.islower() and (ord(char) - ord('a')) % 2 == 0)
```

Full precision:

```python
def split_words(txt):
    if ' ' in txt:
        return txt.split()
    elif ',' in txt:
        return txt.split(',')
    else:
        return sum(1 for char in txt if char.islower() and (ord(char) - ord('a')) % 2 == 1)
```

### HumanEval/146 — recovered (all digits versus boundary digits)

Q4_K_M:

```python
def specialFilter(nums):
    def is_odd_and_greater_than_10(num):
        if num <= 10:
            return False
        digits = [int(d) for d in str(abs(num))]
        return all(d % 2 != 0 for d in digits)
    
    return sum(is_odd_and_greater_than_10(num) for num in nums)

# Test cases
print(specialFilter([15, -73, 14, -15]))  # Output: 1
print(specialFilter([33, -2, -3, 45, 21, 109]))  # Output: 2
```

Full precision:

```python
def specialFilter(nums):
    def is_odd_and_greater_than_10(num):
        if num <= 10:
            return False
        num_str = str(abs(num))
        return int(num_str[0]) % 2 == 1 and int(num_str[-1]) % 2 == 1
    
    return sum(is_odd_and_greater_than_10(num) for num in nums)
```

### HumanEval/141 — lost (overconstrained regex)

Q4_K_M:

```python
def file_name_check(file_name):
    allowed_extensions = {'txt', 'exe', 'dll'}
    parts = file_name.split('.')
    
    if len(parts) != 2:
        return 'No'
    
    name, extension = parts
    
    if not name or not name[0].isalpha():
        return 'No'
    
    digit_count = sum(c.isdigit() for c in name)
    
    if digit_count > 3 or extension not in allowed_extensions:
        return 'No'
    
    return 'Yes'
```

Full precision:

```python
import re

def file_name_check(file_name):
    pattern = r'^[a-zA-Z][^\d]*\d{0,3}[^\d]*\.(txt|exe|dll)$'
    return 'Yes' if re.match(pattern, file_name) else 'No'
```

### HumanEval/155 — lost (zero edge case)

Q4_K_M:

```python
def even_odd_count(num):
    num = abs(num)
    even_count = sum(1 for digit in str(num) if int(digit) % 2 == 0)
    odd_count = sum(1 for digit in str(num) if int(digit) % 2 != 0)
    return (even_count, odd_count)
```

Full precision:

```python
def even_odd_count(num):
    num = abs(num)
    even_count = 0
    odd_count = 0
    while num > 0:
        digit = num % 10
        if digit % 2 == 0:
            even_count += 1
        else:
            odd_count += 1
        num //= 10
    return (even_count, odd_count)
```

## Dev-set replication

This full-set result reproduces both task-level flips observed earlier in the
20-problem HumanEval-Dev comparison committed in `3ae70c2`:

- **HumanEval/46:** Q4_K_M failed and full precision passed in both the dev-set
  and 164-task runs. In both full-set artifacts the decisive code change is the
  recurrence boundary `range(3, n + 1)` to `range(4, n + 1)`.
- **HumanEval/155:** Q4_K_M passed and full precision failed in both the dev-set
  and 164-task runs. In both cases the full-precision arithmetic loop omitted
  the `num == 0` edge case that the Q4 string-based implementation handled.

The dev comparison had equal aggregate accuracy (17/20 for each configuration)
because these two opposing flips cancelled. Their exact recurrence in the
full-set comparison shows that the task-level precision/backend sensitivity is
reproducible across sample sizes, while the additional eight flips explain why
the complete benchmark reveals a non-zero aggregate gap. This strengthens the
decision to use quantized runs for pipeline development and full-precision runs
for capability claims, without treating every observed flip as a causal effect
of quantization alone.
