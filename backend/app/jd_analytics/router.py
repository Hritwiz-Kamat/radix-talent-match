from pathlib import Path
from fastapi import APIRouter, HTTPException
from langchain_community.document_loaders import PyPDFLoader
from app.schemas import ExtractedSkillList
from app.core.extract import extract_skills

router = APIRouter(prefix="/api/jd-analytics", tags=["JD Analytics"])

@router.post("/parse-jd", response_model=ExtractedSkillList)
def parse_jd(filename: str = "sample_google_swe.pdf"):
    """Extracts skills from a Job Description PDF using the shared LLM pipeline."""
    # Navigate up from app/jd_analytics to the backend root, then into data/jds
    file_path = Path(__file__).parent.parent.parent / "data" / "jds" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
    loader = PyPDFLoader(str(file_path))
    raw_text = "\n".join([page.page_content for page in loader.load()])
    
    # JD-specific instructions to append to the master prompt
    task_instructions = (
        "Analyze this Job Description. Extract all technical and soft skills required "
        "by the employer. Pay special attention to determining whether the importance "
        "of each skill is 'required' or 'preferred'."
    )
    
    # Execute the shared pipeline with caching and Pydantic validation
    return extract_skills(
        text=raw_text,
        source_type="jd",
        source_file=filename,
        task_instructions=task_instructions
    )

# from pathlib import Path
# from fastapi import APIRouter, HTTPException
# from langchain_community.document_loaders import PyPDFLoader
# from app.schemas import ExtractedSkillList

# router = APIRouter(prefix="/api/jd-analytics", tags=["JD Analytics"])

# @router.post("/parse-jd", response_model=ExtractedSkillList)
# def parse_jd(filename: str = "sample_google_swe.pdf"):
#     # Navigate up from app/jd_analytics to the backend root, then into data/jds
#     file_path = Path(__file__).parent.parent.parent / "data" / "jds" / filename
    
#     if not file_path.exists():
#         raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
#     loader = PyPDFLoader(str(file_path))
#     raw_text = "\n".join([page.page_content for page in loader.load()])
    
    # PENDING: Pass raw_text to the shared core/extract.py logic

# from fastapi import APIRouter
# from app.schemas import ExtractedSkillList, Skill

# router = APIRouter(prefix="/api/jd-analytics", tags=["JD Analytics"])

# @router.post("/parse-jd", response_model=ExtractedSkillList)
# def parse_jd(filename: str = "sample_google_swe.pdf"):
#     """
#     Temporary mock endpoint. 
#     Role 5 can call this to get valid mock JD data immediately.
#     """
#     return ExtractedSkillList(
#         source_type="jd",
#         source_file=filename,
#         company="Google LLC",
#         role="Software Engineer",
#         skills=[
#             Skill(
#                 skill_name="Python",
#                 category_code="COD",
#                 evidence="Strong proficiency in Python required",
#                 confidence="high",
#                 importance="required"
#             ),
#             Skill(
#                 skill_name="Data Structures",
#                 category_code="DSA",
#                 evidence="Solid understanding of data structures",
#                 confidence="high",
#                 importance="required"
#             )
#         ]
#     )