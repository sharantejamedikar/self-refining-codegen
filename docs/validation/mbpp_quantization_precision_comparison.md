# Qwen2.5-Coder-7B precision comparison on MBPP-427

## Result

On the 427-task sanitized MBPP benchmark, the authoritative local Q4_K_M run
solved 311 problems (`pass@1_single = 311/427 = 0.7283`) and the
full-precision (`bfloat16`) cluster run solved 307
(`307/427 = 0.7190`). The observed change is **-4 net problems, or -0.94
percentage points** (-0.9368 points before rounding; -0.93 points when the two
four-decimal displayed rates are subtracted). Twenty outcomes changed: full
precision recovered eight Q4 failures and lost twelve Q4 successes.

This is the first precision comparison in this project in which the
full-precision reporting configuration scored below Q4_K_M. It contrasts with
HumanEval single-pass, where full precision gained 6/164 (+3.66 points), and
with the other completed HumanEval comparisons, which also showed a net
full-precision advantage. The MBPP result is therefore important evidence
against treating quantization as a monotonic degradation or applying the
HumanEval precision gap as a correction factor to another benchmark.

The direction reversal is small and should not be overinterpreted. With 20
discordant pairs, an exact two-sided McNemar test (equivalently, a two-sided
binomial test conditional on the discordant count) gives `p = 0.5034` for an
8-versus-12 split. The observed data do not establish that Q4_K_M is generally
better on MBPP. Rather, they show that low-temperature generation remains
sensitive to numerical representation and inference implementation, and that
the resulting task-level gains and losses can nearly cancel or reverse sign on
a particular benchmark.

As with the HumanEval comparison, this is an **end-to-end configuration gap,
not a clean causal estimate of weight quantization alone**. Precision,
inference backend, hardware, and execution host changed together
(Ollama/CPU Q4_K_M versus Hugging Face/CUDA `bfloat16`). Unlike HumanEval/39,
none of the 20 MBPP flips was caused by a missing execution dependency: each
was attributable to different generated code. A causal quantization study
would hold the inference and execution stacks fixed and vary only the weight
representation.

## Methodology and controls

The paired runs were:

- Q4_K_M: [`20260716T171911.599683Z_m7_quantized_local_development_single_mbpp_full`](../../experiments/results/20260716T171911.599683Z_m7_quantized_local_development_single_mbpp_full/)
- Full precision: [`20260809T100420.122030Z_cluster_qwen_hf_zero_shot_mbpp_full`](../../experiments/results/20260809T100420.122030Z_cluster_qwen_hf_zero_shot_mbpp_full/)

The Q4 artifact is the corrected, authoritative run made at guard commit
`77f91a713db0322526420d4bfaa9a2cf55eadf92`. The earlier `163337` MBPP run is
the documented stale-prompt artifact and is excluded from this comparison.

The comparison held fixed the canonical model
`Qwen/Qwen2.5-Coder-7B-Instruct`, Hugging Face revision
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, 427-task sanitized dataset and
source URL, task IDs, zero-shot prompt strategy, system and user prompts,
tests, seed 42, temperature 0.2, top-p 0.95, maximum 512 new tokens,
repetition penalty 1.1, subprocess executor, 10-second timeout, and 512 MiB
memory limit. Both artifacts record their config snapshot, git commit, seeds,
per-problem JSON, and summary CSV.

The intended treatment was model precision. The local run used Ollama
`qwen2.5-coder:7b-instruct-q4_K_M` (digest
`dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`);
the cluster loaded the pinned Hugging Face revision as `torch.bfloat16`
without quantization. Identical seeds are matched reproducibility metadata,
not a guarantee of token-identical sampling across these implementations.

## Outcome flips

| Problem | Q4_K_M | Full precision | Direction | One-line code-level explanation |
|---|---:|---:|---|---|
| MBPP/103 | Fail | Pass | Recovered | Full precision gives the Eulerian recurrence its required `m == 0` base value of 1; Q4 returned 0. |
| MBPP/245 | Fail | Pass | Recovered | Full precision initializes every decreasing-subsequence accumulator to its element; Q4 left `dec` at zero. |
| MBPP/278 | Fail | Pass | Recovered | Full precision counts elements before the first nested tuple; Q4 always returned the outer tuple length minus one. |
| MBPP/424 | Fail | Pass | Recovered | Both extract the same characters, but full precision returns the required list while Q4 returns a tuple. |
| MBPP/592 | Fail | Pass | Recovered | Full precision sums `C(n,i-1)C(n,i)`; Q4 incorrectly used the loop index as the binomial upper argument. |
| MBPP/644 | Fail | Pass | Recovered | Full precision treats `k` as an exclusive prefix length; Q4 reversed through index `k` inclusively. |
| MBPP/726 | Fail | Pass | Recovered | Full precision references `test_tup`; Q4 references undefined variable `tup` and raises `NameError`. |
| MBPP/809 | Fail | Pass | Recovered | Full precision tests whether every first-tuple element is greater; Q4 reversed the comparison. |
| MBPP/61 | Pass | Fail | Lost | Q4 tracks prefixes of digit-sum minus prefix length; full precision substitutes a whole-string expression and undercounts. |
| MBPP/71 | Pass | Fail | Lost | Full precision sorts in place but omits the required return value; Q4 returns `nums`. |
| MBPP/72 | Pass | Fail | Lost | Q4 implements the tested `n % 4 != 2` condition; full precision uses a different parity predicate. |
| MBPP/123 | Pass | Fail | Lost | Full precision adds only the smaller member of each amicable pair (`partner > num`); Q4 adds both members as required by the tests. |
| MBPP/229 | Pass | Fail | Lost | Full precision stably moves negatives with `pop`/`insert`; Q4's swaps produce the tested non-stable positive ordering. |
| MBPP/388 | Pass | Fail | Lost | Full precision calls `math.log2` without importing `math`; Q4 uses the import-free integer `bit_length`. |
| MBPP/410 | Pass | Fail | Lost | Full precision applies `min` to mixed strings and numbers and raises `TypeError`; Q4 filters to numeric values. |
| MBPP/419 | Pass | Fail | Lost | Full precision prints the computed value and implicitly returns `None`; Q4 returns it. |
| MBPP/421 | Pass | Fail | Lost | Full precision concatenates without separators; Q4 joins with the required hyphens. |
| MBPP/581 | Pass | Fail | Lost | Full precision interprets `s` as slant height and derives a vertical height; Q4 uses the tested formula directly. |
| MBPP/643 | Pass | Fail | Lost | Full precision accepts any word containing `z`, including at an edge; Q4 requires `z` in the middle via `\Bz\B`. |
| MBPP/735 | Pass | Fail | Lost | Full precision constructs the wrong XOR mask and toggles endpoint bits; Q4 masks exactly the middle bits. |

The eight recoveries and twelve losses yield the observed net change of -4.

## Generated-code audit

The following is the exact extracted `generation.code` from each per-problem
JSON record. Whitespace and comments are retained.

### MBPP/103 — recovered (Eulerian base case)

Q4_K_M:

```python
def eulerian_num(n, m):
    if m >= n or n == 0 or m == 0:
        return 0
    if n == m:
        return 1
    return ((n - m) * eulerian_num(n - 1, m - 1) + (m + 1) * eulerian_num(n - 1, m))
```

Full precision:

```python
def eulerian_num(n, m):
    if m >= n or n == 0:
        return 0
    if m == 0:
        return 1
    return ((n - m) * eulerian_num(n - 1, m - 1) + (m + 1) * eulerian_num(n - 1, m))
```

### MBPP/245 — recovered (decreasing-subsequence initialization)

Q4_K_M:

```python
def max_sum(arr):
    n = len(arr)
    inc = [0] * n
    dec = [0] * n
    
    for i in range(n):
        inc[i] = arr[i]
    
    for i in range(1, n):
        for j in range(i):
            if arr[i] > arr[j] and inc[i] < inc[j] + arr[i]:
                inc[i] = inc[j] + arr[i]
    
    for i in range(n-2, -1, -1):
        for j in range(n-1, i, -1):
            if arr[i] > arr[j] and dec[i] < dec[j] + arr[i]:
                dec[i] = dec[j] + arr[i]
    
    max_sum = 0
    for i in range(n):
        max_sum = max(max_sum, inc[i] + dec[i] - arr[i])
    
    return max_sum
```

Full precision:

```python
def max_sum(arr):
    n = len(arr)
    inc = [0] * n
    dec = [0] * n
    
    # Compute maximum sum increasing subsequence for each element
    for i in range(n):
        inc[i] = arr[i]
        for j in range(i):
            if arr[i] > arr[j] and inc[i] < inc[j] + arr[i]:
                inc[i] = inc[j] + arr[i]
    
    # Compute maximum sum decreasing subsequence for each element
    for i in range(n-1, -1, -1):
        dec[i] = arr[i]
        for j in range(i+1, n):
            if arr[i] > arr[j] and dec[i] < dec[j] + arr[i]:
                dec[i] = dec[j] + arr[i]
    
    # Find the maximum sum of bitonic subsequence
    max_bitonic_sum = 0
    for i in range(n):
        max_bitonic_sum = max(max_bitonic_sum, inc[i] + dec[i] - arr[i])
    
    return max_bitonic_sum
```

### MBPP/278 — recovered (first nested-tuple boundary)

Q4_K_M:

```python
def count_first_elements(test_tup):
    return len(test_tup) - 1 if isinstance(test_tup, tuple) and len(test_tup) > 0 else 0
```

Full precision:

```python
def count_first_elements(test_tup):
    # Initialize counter for elements before the first tuple element
    count = 0
    
    # Iterate through each element in the tuple
    for ele in test_tup:
        # Check if the current element is a tuple
        if isinstance(ele, tuple):
            break
        # Increment counter for non-tuple elements
        count += 1
    
    return count
```

### MBPP/424 — recovered (return container type)

Q4_K_M:

```python
def extract_rear(test_tuple):
    result = tuple(item[-1] for item in test_tuple)
    return result
```

Full precision:

```python
def extract_rear(test_tuple):
    # Using list comprehension to iterate through each string in the tuple
    # and extracting the last character using negative indexing.
    result = [sub[-1] for sub in test_tuple]
    return result
```

### MBPP/592 — recovered (binomial upper argument)

Q4_K_M:

```python
from math import comb

def sum_Of_product(n):
    total_sum = 0
    for i in range(1, n+1):
        total_sum += comb(i, 1) * comb(i, 2)
    return total_sum
```

Full precision:

```python
from math import comb

def sum_Of_product(n):
    total_sum = 0
    for i in range(1, n+1):
        total_sum += comb(n, i-1) * comb(n, i)
    return total_sum
```

### MBPP/644 — recovered (exclusive prefix length)

Q4_K_M:

```python
def reverse_Array_Upto_K(input, k):
    # Reverse elements from the start up to index k (inclusive)
    input[:k+1] = reversed(input[:k+1])
    return input
```

Full precision:

```python
def reverse_Array_Upto_K(input, k):
    # Reverse the elements from index 0 to k-1
    input[:k] = reversed(input[:k])
    return input
```

### MBPP/726 — recovered (undefined variable)

Q4_K_M:

```python
def multiply_elements(test_tup):
    return tuple(tup[i] * tup[i + 1] for i in range(len(tup) - 1))
```

Full precision:

```python
def multiply_elements(test_tup):
    result = tuple(t1 * t2 for t1, t2 in zip(test_tup, test_tup[1:]))
    return result
```

### MBPP/809 — recovered (comparison direction)

Q4_K_M:

```python
def check_smaller(test_tup1, test_tup2):
    return all(x < y for x, y in zip(test_tup1, test_tup2))
```

Full precision:

```python
def check_smaller(test_tup1, test_tup2):
    # Using all() and zip() to compare elements of both tuples
    result = all(x > y for x, y in zip(test_tup1, test_tup2))
    return result
```

### MBPP/61 — lost (prefix invariant)

Q4_K_M:

```python
def count_Substrings(s):
    count = 0
    total_sum = 0
    prefix_sum_count = {0: 1}
    
    for i, char in enumerate(s):
        total_sum += int(char)
        
        if (total_sum - (i + 1)) in prefix_sum_count:
            count += prefix_sum_count[total_sum - (i + 1)]
        
        if total_sum - (i + 1) not in prefix_sum_count:
            prefix_sum_count[total_sum - (i + 1)] = 0
        prefix_sum_count[total_sum - (i + 1)] += 1
    
    return count
```

Full precision:

```python
from collections import defaultdict

def count_Substrings(s):
    count = 0
    prefix_sum = 0
    prefix_map = defaultdict(int)
    prefix_map[0] = 1
    
    for char in s:
        prefix_sum += int(char)
        if prefix_sum - (len(s) - prefix_sum) == 0:
            count += 1
        count += prefix_map[prefix_sum - (len(s) - prefix_sum)]
        prefix_map[prefix_sum - (len(s) - prefix_sum)] += 1
    
    return count
```

### MBPP/71 — lost (missing return)

Q4_K_M:

```python
def comb_sort(nums):
    gap = len(nums)
    shrink_factor = 1.3
    sorted = False

    while not sorted or gap > 1:
        if gap > 1:
            gap = int(gap / shrink_factor)

        sorted = True
        for i in range(len(nums) - gap):
            if nums[i] > nums[i + gap]:
                nums[i], nums[i + gap] = nums[i + gap], nums[i]
                sorted = False

    return nums
```

Full precision:

```python
def comb_sort(nums):
    gap = len(nums)
    shrink_factor = 1.3
    sorted = False

    while not sorted:
        gap = int(gap / shrink_factor)
        if gap <= 1:
            gap = 1
            sorted = True

        for i in range(len(nums) - gap):
            if nums[i] > nums[i + gap]:
                nums[i], nums[i + gap] = nums[i + gap], nums[i]
                sorted = False
```

### MBPP/72 — lost (wrong modular predicate)

Q4_K_M:

```python
def dif_Square(n):
    return n % 4 != 2
```

Full precision:

```python
def dif_Square(n):
    return n % 2 == 0 or n % 4 != 3
```

### MBPP/123 — lost (one-sided amicable-pair accumulation)

Q4_K_M:

```python
def amicable_numbers_sum(limit):
    def sum_of_divisors(n):
        return sum(i for i in range(1, n) if n % i == 0)

    total_sum = 0
    for num in range(2, limit + 1):
        div_sum = sum_of_divisors(num)
        if div_sum != num and sum_of_divisors(div_sum) == num:
            total_sum += num

    return total_sum
```

Full precision:

```python
def amicable_numbers_sum(limit):
    def sum_of_divisors(n):
        return sum(i for i in range(1, n) if n % i == 0)

    amicable_sum = 0
    for num in range(2, limit + 1):
        partner = sum_of_divisors(num)
        if partner > num and sum_of_divisors(partner) == num:
            amicable_sum += num

    return amicable_sum
```

### MBPP/229 — lost (stable movement versus tested swaps)

Q4_K_M:

```python
def re_arrange_array(arr, n):
    neg_index = 0
    for i in range(n):
        if arr[i] < 0:
            arr[neg_index], arr[i] = arr[i], arr[neg_index]
            neg_index += 1
    return arr
```

Full precision:

```python
def re_arrange_array(arr, n):
    neg_index = 0
    for i in range(n):
        if arr[i] < 0:
            arr.insert(neg_index, arr.pop(i))
            neg_index += 1
    return arr
```

### MBPP/388 — lost (missing import)

Q4_K_M:

```python
def highest_Power_of_2(n):
    return 2 ** int(n.bit_length() - 1)
```

Full precision:

```python
def highest_Power_of_2(n):
    return 2 ** int(math.log2(n))
```

### MBPP/410 — lost (mixed-type minimum)

Q4_K_M:

```python
def min_val(listval):
    if not listval:
        return None  # Return None if the list is empty
    
    min_value = float('inf')  # Initialize with infinity
    
    for item in listval:
        if isinstance(item, (int, float)) and item < min_value:
            min_value = item
    
    return min_value
```

Full precision:

```python
def min_val(listval):
    return min(listval)
```

### MBPP/419 — lost (printed instead of returned)

Q4_K_M:

```python
def round_and_sum(list1):
    rounded_sum = sum([round(num) for num in list1])
    return rounded_sum * len(list1)
```

Full precision:

```python
def round_and_sum(list1):
    rounded_sum = sum(round(num) for num in list1)
    result = rounded_sum * len(list1)
    print(result)
```

### MBPP/421 — lost (missing separators)

Q4_K_M:

```python
def concatenate_tuple(test_tup):
    res = '-'.join(str(ele) for ele in test_tup)
    return res
```

Full precision:

```python
def concatenate_tuple(test_tup):
    # Initialize an empty string to store the result
    res = ''
    # Iterate through each element in the tuple
    for ele in test_tup:
        # Concatenate the current element with the result string
        res += str(ele)
    return res
```

### MBPP/581 — lost (formula interpretation)

Q4_K_M:

```python
import math

def surface_Area(b, s):
    return b * b + 2 * b * s
```

Full precision:

```python
import math

def surface_Area(b, s):
    return b * b + 2 * b * math.sqrt(s * s - (b / 2) * (b / 2))
```

### MBPP/643 — lost (`z` word position)

Q4_K_M:

```python
import re

def text_match_wordz_middle(text):
    pattern = r'\Bz\B'
    return bool(re.search(pattern, text))
```

Full precision:

```python
import re

def text_match_wordz_middle(text):
    pattern = r'\b\w*z\w*\b'
    return bool(re.search(pattern, text))
```

### MBPP/735 — lost (middle-bit mask)

Q4_K_M:

```python
def toggle_middle_bits(n):
    # Calculate the number of bits in n
    num_bits = n.bit_length()
    
    # Create a mask with all bits set except the first and last bit
    if num_bits <= 2:
        return n  # No middle bits to toggle
    
    mask = ((1 << (num_bits - 1)) - 1) ^ 1
    
    # Toggle the middle bits using the XOR operation
    result = n ^ mask
    
    return result
```

Full precision:

```python
def toggle_middle_bits(n):
    # Calculate the number of bits in n
    num_bits = n.bit_length()
    
    # If there are less than 3 bits, return n as no middle bits to toggle
    if num_bits < 3:
        return n
    
    # Create a mask with all bits set except the first and last bits
    mask = ((1 << (num_bits - 2)) - 1) ^ ((1 << (num_bits - 1)))
    
    # Toggle the middle bits using the mask
    result = n ^ mask
    
    return result
```

## Interpretation: why can full precision be slightly worse here?

The code audit does not reveal one systematic full-precision failure mode.
The twelve losses span missing return/import mistakes (MBPP/71, /388, /419),
misread output contracts (MBPP/421, /643), incorrect mathematical predicates
or formulas (MBPP/61, /72, /123, /581, /735), and a benchmark-specific
ordering choice (MBPP/229). The eight recoveries are similarly heterogeneous:
base cases, initialization, boundaries, container type, variable naming, and
comparison direction. This mixture is consistent with a small change in the
sampled generation path moving individual tasks across a pass/fail boundary,
not with a single capability that quantization consistently improved.

Three features make a sign reversal plausible:

1. **Pass@1 is discontinuous.** A one-token change such as `return` versus
   `print`, `<` versus `>`, or `k` versus `k+1` changes a task from fully
   correct to fully incorrect. Twenty changed generations can therefore
   produce a small net difference even if neither configuration dominates.
2. **The configurations are not token-coupled.** Ollama and Hugging Face use
   different inference implementations, and quantized and `bfloat16` logits
   need not select the same tokens under sampling. Seed 42 reproduces each
   configuration; it does not force a paired token trajectory between them.
3. **MBPP prompts are short and sometimes underspecified without examples.**
   Several flips turn on conventions not fully determined by a terse task
   description: return container type, hyphen insertion, whether an argument
   is slant height, and whether rearrangement should be stable. Small decoding
   changes can select different plausible implementations, while the hidden
   tests credit only one interpretation.

Consequently, the defensible conclusion is narrow: on this fixed MBPP-427
single-pass run, the full-precision reporting configuration scored 4 tasks
lower than the local Q4_K_M configuration. It does **not** show that
quantization improves Qwen generally, nor does it overturn the requirement to
use full-precision results for dissertation claims. It does show why local Q4
results must be labelled as development measurements and why precision/backend
effects should be reported separately by benchmark and experiment rather than
assumed to have a uniform direction.
