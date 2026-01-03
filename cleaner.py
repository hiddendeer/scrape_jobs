import re

def clean_salary(salary_raw):
    """
    Parses salary string like '15-25K', '15-25K·14薪'
    Returns tuple (min, max, avg, months)
    """
    if not salary_raw:
        return 0, 0, 0, 12

    salary_min = 0
    salary_max = 0
    salary_months = 12
    
    # Extract months if present (e.g. "·14薪")
    months_match = re.search(r'·(\d+)薪', salary_raw)
    if months_match:
        salary_months = int(months_match.group(1))

    # Handle K (Monthly)
    k_match = re.search(r'(\d+)-(\d+)K', salary_raw, re.IGNORECASE)
    if k_match:
        salary_min = int(k_match.group(1)) * 1000
        salary_max = int(k_match.group(2)) * 1000
    else:
        # Handle 'Day' or other formats specifically if needed, likely just raw numbers
        day_match = re.search(r'(\d+)-(\d+)元/天', salary_raw)
        if day_match:
             salary_min = int(day_match.group(1))
             salary_max = int(day_match.group(2))
    
    salary_avg = (salary_min + salary_max) // 2
    return salary_min, salary_max, salary_avg, salary_months

def clean_exp(exp_raw):
    """
    Parses experience string like '3-5年', '5-10年', '10年以上', '经验不限', '应届生'
    Returns (exp_min, exp_max)
    """
    if not exp_raw:
        return 0, 0
    
    # "3-5年" -> 3, 5
    range_match = re.search(r'(\d+)-(\d+)年', exp_raw)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    
    # "10年以上" -> 10, 99
    above_match = re.search(r'(\d+)年以上', exp_raw)
    if above_match:
        return int(above_match.group(1)), 99
        
    # "1年以内" -> 0, 1
    within_match = re.search(r'(\d+)年以内', exp_raw)
    if within_match:
        return 0, int(within_match.group(1))
    
    # "经验不限" -> 0, 0 (or 0, 99 depending on detailed logic, typically 0 min)
    # "应届生" -> 0, 0
    return 0, 0

def standardize_job(job_data):
    """
    Standardizes job data dictionary.
    """
    salary_min, salary_max, salary_avg, salary_months = clean_salary(job_data.get('salaryDesc'))
    exp_min, exp_max = clean_exp(job_data.get('jobExperience'))
    
    return {
        'job_id': job_data.get('encryptJobId'),
        'job_name': job_data.get('jobName'),
        'company_name': job_data.get('brandName'),
        'city': job_data.get('cityName'),
        'district': job_data.get('areaDistrict'), # New field
        'salary_raw': job_data.get('salaryDesc'),
        'salary_min': salary_min,
        'salary_max': salary_max,
        'salary_avg': salary_avg,
        'salary_months': salary_months, # New field
        'experience_raw': job_data.get('jobExperience'), # Renamed from exp_raw
        'exp_min': exp_min,
        'exp_max': exp_max, # New field
        'education': job_data.get('jobDegree'),
        'skills_tags': job_data.get('skills', []),
        'job_desc': job_data.get('job_desc'),
        'detail_url': f"https://www.zhipin.com/job_detail/{job_data.get('encryptJobId')}.html"
    }
