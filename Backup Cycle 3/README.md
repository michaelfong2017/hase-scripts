# Jobs
## Cycle 3
```bash
job 67400 - full3680 8B - 2GPUs
-> inference job 67435
job 67401 - full3680 32B - 4GPUs
-> inference job 67436
job 67402 - inference full60 base 8B
job 67403 - inference full60 base 32B
job 67404 - inference full60 base 14B
job 67405 - inference full60 base 7B

job 67410 - full3680 14B - 3GPUs
job 67411 - full3680 7B - 2GPUs


Test on Cycle 2 final models on full60
job_65239_20250616_0838_Llama3.1-8B-Instruct_LoRA -> job 67406
job_65243_20250616_1015_Qwen2.5-32B-Instruct_LoRA -> job 64707
job_65282_20250616_1709_Qwen2.5-14B-Instruct_LoRA -> job 64708
job_65283_20250616_1541_Qwen2.5-7B-Instruct_LoRA -> job 64709


Try Fixing Fine-tune and Testing scripts:
job 67443 - full3680 32B - 4GPUs - lora_r16 lora_alpha32 sequence10000



final v5
job 67612 - full3680 32B - 4GPUs
-> inference job 67613

job 67711 - inference full60 base 32B

job 67712 - inference full60 Cycle2 32B


Only beneficiary is correct (from victim transaction) -> still potentially match



hase.forms.michael@klb-login-01:/home/projects/fraudagent/hase-michael/V4$ sbatch r3680-14b-lora.sh
Submitted batch job 67688 (STOPPED)
hase.forms.michael@klb-login-01:/home/projects/fraudagent/hase-michael/V4$ sbatch r3680-8b-lora.sh
Submitted batch job 67689 (STOPPED)


hase.forms.michael@klb-login-01:/home/projects/fraudagent/hase-michael/V4$ sbatch r3680-8b-lora.sh
Submitted batch job 67734
-> inference job 67745
hase.forms.michael@klb-login-01:/home/projects/fraudagent/hase-michael/V4$ sbatch r3680-14b-lora.sh
Submitted batch job 67735
-> 
hase.forms.michael@klb-login-01:/home/projects/fraudagent/hase-michael/V4$ sbatch r3680-7b-lora.sh
Submitted batch job 67736
-> inference job 67746


job 67747 - inference full60 base 14B
job 67748 - inference full60 base 7B
job 67749 - inference full60 base 8B


full60 inference (some do again):
job 67757 - Cycle 3 job_67612_20250703_0714_Qwen2.5-32B-Instruct_LoRA
job 67758 - Cycle 2 job_65243_20250616_1015_Qwen2.5-32B-Instruct_LoRA
job 67759 - Base 32B

job 67761 - Cycle 3 job_67734_20250703_1713_Llama3.1-8B-Instruct_LoRA
job 67762 - Cycle 2 job_65239_20250616_0838_Llama3.1-8B-Instruct_LoRA
job 67763 - Base 8B

job 67764 - Cycle 3 job_67736_20250703_1713_Qwen2.5-7B-Instruct_LoRA
job 67765 - Cycle 2 job_65283_20250616_1541_Qwen2.5-7B-Instruct_LoRA
job 67766 - Base 7B

job 67767 - Cycle 3 job_67735_20250703_2110_Qwen2.5-14B-Instruct_LoRA
job 67768 - Cycle 2 job_65282_20250616_1709_Qwen2.5-14B-Instruct_LoRA
job 67769 - Base 14B

job 67770 - Cycle 2 job_65363_20250616_1828_Llama-3.2-3B-Instruct_LoRA
job 67771 - Cycle 2 job_65364_20250616_1930_Llama-3.2-1B-Instruct_LoRA
job 67772 - Base Llama 3B
job 67773 - Base Llama 1B


Exam18 (FORGOT TRANSACTION ID)
job 67774 - Cycle 3 job_67612_20250703_0714_Qwen2.5-32B-Instruct_LoRA
job 67775 - Cycle 2 job_65243_20250616_1015_Qwen2.5-32B-Instruct_LoRA
job 67776 - Base 32B

job 67777 - Cycle 3 job_67734_20250703_1713_Llama3.1-8B-Instruct_LoRA
job 67778 - Cycle 2 job_65239_20250616_0838_Llama3.1-8B-Instruct_LoRA
job 67779 - Base 8B


Exam18
job 67833 - Cycle 3 job_67612_20250703_0714_Qwen2.5-32B-Instruct_LoRA
job 67834 - Cycle 2 job_65243_20250616_1015_Qwen2.5-32B-Instruct_LoRA
job 67836 - Base 32B

job 67837 - Cycle 3 job_67734_20250703_1713_Llama3.1-8B-Instruct_LoRA
job 67838 - Cycle 2 job_65239_20250616_0838_Llama3.1-8B-Instruct_LoRA
job 67839 - Base 8B

job 67841 - Cycle 3 job_67736_20250703_1713_Qwen2.5-7B-Instruct_LoRA
job 67842 - Cycle 2 job_65283_20250616_1541_Qwen2.5-7B-Instruct_LoRA
job 67843 - Base 7B

job 67848 - Cycle 3 job_67735_20250703_2110_Qwen2.5-14B-Instruct_LoRA
job 67849 - Cycle 2 job_65282_20250616_1709_Qwen2.5-14B-Instruct_LoRA
job 67850 - Base 14B

job 67851 - Cycle 2 job_65363_20250616_1828_Llama-3.2-3B-Instruct_LoRA
job 67852 - Cycle 2 job_65364_20250616_1930_Llama-3.2-1B-Instruct_LoRA
job 67853 - Base Llama 3B
job 67854 - Base Llama 1B


full4355 training
job 67902 - Cycle 3 job_67902_20250704_1444_Qwen2.5-32B-Instruct_LoRA
-> exam18v1 inference job 67913
-> full60 inference job 67914
-> exam18v2 inference job 68037
-> exam18v3 inference job 68038
-> exam18v3 rematch unlocated inference job 68068 (pre-2 version is job 68051, no channel rules) (pre-1 version is job 68045, no merging rules)

job 67968 - Cycle 3 job_67968_20250704_2328_Qwen2.5-14B-Instruct_LoRA
-> full60 inference job 68029
-> exam18v2 inference job 68035
-> exam18v3 inference job 68036
-> exam18v3 rematch unlocated inference job 68069 (pre-2 version is job 68053, no channel rules) (pre version is job 68046, no merging rules)


SECOND TUNE (v5)
/home/projects/fraudagent/all-downloads/job_67734_20250703_1713_Llama3.1-8B-Instruct_LoRA_job_67979
-> second675 job 68043 - Cycle 3 job_68043_20250705_1937_job_67734_20250703_1713_Llama3.1-8B-Instruct_LoRA_job_67979_LoRA
-> merge job 68047
-> exam18v2 inference job 68054
-> exam18v3 inference job 68055
-> exam18v3 rematch unlocated inference job 68070 (pre-2 version is job 68058, no channel rules)

/home/projects/fraudagent/all-downloads/job_67736_20250703_1713_Qwen2.5-7B-Instruct_LoRA_job_67981
-> second675 job 68044 - Cycle 3 job_68044_20250705_1937_job_67736_20250703_1713_Qwen2.5-7B-Instruct_LoRA_job_67981_LoRA
-> merge job 68048
-> exam18v2 inference job 68056
-> exam18v3 inference job 68057
-> exam18v3 rematch unlocated inference job 68071 (pre-2 version is job 68059, no channel rules)


MERGE JOB
Qwen 32B
job 67976 - Cycle 3 job_67902_20250704_1444_Qwen2.5-32B-Instruct_LoRA
job 67977 - Cycle 3 job_67612_20250703_0714_Qwen2.5-32B-Instruct_LoRA
job 67978 - Cycle 2 job_65243_20250616_1015_Qwen2.5-32B-Instruct_LoRA

Llama 8B
job 67979 - Cycle 3 job_67734_20250703_1713_Llama3.1-8B-Instruct_LoRA
job 67980 - Cycle 2 job_65239_20250616_0838_Llama3.1-8B-Instruct_LoRA

Qwen 7B
job 67981 - Cycle 3 job_67736_20250703_1713_Qwen2.5-7B-Instruct_LoRA
job 67982 - Cycle 2 job_65283_20250616_1541_Qwen2.5-7B-Instruct_LoRA

Qwen 14B
job 68030 - Cycle 3 job_67968_20250704_2328_Qwen2.5-14B-Instruct_LoRA
job 67983 - Cycle 3 job_67735_20250703_2110_Qwen2.5-14B-Instruct_LoRA
job 67984 - Cycle 2 job_65282_20250616_1709_Qwen2.5-14B-Instruct_LoRA

Llama 3B & 1B
job 67985 - Cycle 2 job_65363_20250616_1828_Llama-3.2-3B-Instruct_LoRA
job 67986 - Cycle 2 job_65364_20250616_1930_Llama-3.2-1B-Instruct_LoRA
```

## V6 (WORSE)
```bash
V6 (WORSE)
job 68004 - Cycle 3 full4380 - job_68004_20250705_0854_Qwen2.5-32B-Instruct_LoRA
-> merge job 68005

/home/projects/fraudagent/all-downloads/job_68004_20250705_0854_Qwen2.5-32B-Instruct_LoRA_job_68005
-> inference full60v6 job 68018
-> inference exam18v2.6 (from v6 instruction) job 68028
-> inference exam18v3.6 job 68064
-> inference exam18v3.6 rematch unlocated job 68072

job 68006 - Cycle 3 full4380 - job_68006_20250705_1222_Qwen2.5-14B-Instruct_LoRA
-> merge job 68042
-> inference full60v6 job 68062
-> inference exam18v2.6 (from v6 instruction) job 68063
-> inference exam18v3.6 job 68065
-> inference exam18v3.6 rematch unlocated job 68073

/home/projects/fraudagent/all-downloads/job_68006_20250705_1222_Qwen2.5-14B-Instruct_LoRA_job_68042
```