@echo off
setlocal EnableExtensions

rem ============================================================
rem GRD Document Verification - Project Scaffolder
rem Stack: React + TypeScript + Vite, FastAPI, Celery, Redis,
rem PostgreSQL and MinIO
rem Usage:
rem   create_grd_document_verf.bat
rem   create_grd_document_verf.bat grd-document-verf
rem ============================================================

set "PROJECT_NAME=%~1"
if "%PROJECT_NAME%"=="" set "PROJECT_NAME=grd-document-verf"

echo.
echo Creating project: %PROJECT_NAME%
echo.

where node >nul 2>nul
if errorlevel 1 (
    echo ERROR: Node.js is not installed or is not available in PATH.
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo ERROR: npm is not installed or is not available in PATH.
    exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Python 3 is not installed or is not available in PATH.
        exit /b 1
    )
    set "PYTHON_CMD=python"
)

if exist "%PROJECT_NAME%" (
    echo ERROR: Folder "%PROJECT_NAME%" already exists.
    exit /b 1
)

mkdir "%PROJECT_NAME%"
pushd "%PROJECT_NAME%"

rem ------------------------------------------------------------
rem Root folders
rem ------------------------------------------------------------
mkdir backend
mkdir backend\app
mkdir backend\app\api
mkdir backend\app\api\v1
mkdir backend\app\api\v1\endpoints
mkdir backend\app\core
mkdir backend\app\db
mkdir backend\app\models
mkdir backend\app\schemas
mkdir backend\app\services
mkdir backend\app\workers
mkdir backend\app\utils
mkdir backend\tests
mkdir backend\alembic

mkdir ml
mkdir ml\datasets
mkdir ml\evaluation
mkdir ml\models
mkdir ml\notebooks
mkdir ml\training

mkdir infrastructure
mkdir infrastructure\docker
mkdir infrastructure\monitoring
mkdir infrastructure\nginx

mkdir docs
mkdir storage
mkdir storage\uploads
mkdir storage\processed
mkdir storage\quarantine

rem ------------------------------------------------------------
rem Python package marker files
rem ------------------------------------------------------------
type nul > backend\app\__init__.py
type nul > backend\app\api\__init__.py
type nul > backend\app\api\v1\__init__.py
type nul > backend\app\api\v1\endpoints\__init__.py
type nul > backend\app\core\__init__.py
type nul > backend\app\db\__init__.py
type nul > backend\app\models\__init__.py
type nul > backend\app\schemas\__init__.py
type nul > backend\app\services\__init__.py
type nul > backend\app\workers\__init__.py
type nul > backend\app\utils\__init__.py
type nul > backend\tests\__init__.py

rem ------------------------------------------------------------
rem Backend dependencies
rem ------------------------------------------------------------
> backend\requirements.txt echo fastapi
>> backend\requirements.txt echo uvicorn[standard]
>> backend\requirements.txt echo python-multipart
>> backend\requirements.txt echo pydantic-settings
>> backend\requirements.txt echo sqlalchemy
>> backend\requirements.txt echo alembic
>> backend\requirements.txt echo psycopg[binary]
>> backend\requirements.txt echo celery[redis]
>> backend\requirements.txt echo redis
>> backend\requirements.txt echo boto3
>> backend\requirements.txt echo pillow
>> backend\requirements.txt echo opencv-python-headless
>> backend\requirements.txt echo numpy
>> backend\requirements.txt echo pandas
>> backend\requirements.txt echo scikit-learn
>> backend\requirements.txt echo pymupdf
>> backend\requirements.txt echo pytesseract
>> backend\requirements.txt echo python-jose[cryptography]
>> backend\requirements.txt echo passlib[bcrypt]
>> backend\requirements.txt echo httpx
>> backend\requirements.txt echo pytest
>> backend\requirements.txt echo pytest-asyncio
>> backend\requirements.txt echo ruff

> backend\requirements-ml.txt echo torch
>> backend\requirements-ml.txt echo torchvision
>> backend\requirements-ml.txt echo transformers
>> backend\requirements-ml.txt echo timm
>> backend\requirements-ml.txt echo sentence-transformers
>> backend\requirements-ml.txt echo easyocr

rem ------------------------------------------------------------
rem FastAPI application
rem ------------------------------------------------------------
> backend\app\main.py echo from fastapi import FastAPI
>> backend\app\main.py echo from fastapi.middleware.cors import CORSMiddleware
>> backend\app\main.py echo.
>> backend\app\main.py echo from app.api.v1.router import api_router
>> backend\app\main.py echo.
>> backend\app\main.py echo app = FastAPI^(title="GRD Document Verification API", version="0.1.0"^)
>> backend\app\main.py echo.
>> backend\app\main.py echo app.add_middleware^(
>> backend\app\main.py echo     CORSMiddleware,
>> backend\app\main.py echo     allow_origins=["http://localhost:5173"],
>> backend\app\main.py echo     allow_credentials=True,
>> backend\app\main.py echo     allow_methods=["*"],
>> backend\app\main.py echo     allow_headers=["*"],
>> backend\app\main.py echo ^)
>> backend\app\main.py echo.
>> backend\app\main.py echo app.include_router^(api_router, prefix="/api/v1"^)
>> backend\app\main.py echo.
>> backend\app\main.py echo @app.get^("/health", tags=["Health"]^)
>> backend\app\main.py echo def health^(^):
>> backend\app\main.py echo     return {"status": "ok"}

> backend\app\api\v1\router.py echo from fastapi import APIRouter
>> backend\app\api\v1\router.py echo.
>> backend\app\api\v1\router.py echo from app.api.v1.endpoints import documents, reviews, verification
>> backend\app\api\v1\router.py echo.
>> backend\app\api\v1\router.py echo api_router = APIRouter^(^)
>> backend\app\api\v1\router.py echo api_router.include_router^(documents.router, prefix="/documents", tags=["Documents"]^)
>> backend\app\api\v1\router.py echo api_router.include_router^(verification.router, prefix="/verification", tags=["Verification"]^)
>> backend\app\api\v1\router.py echo api_router.include_router^(reviews.router, prefix="/reviews", tags=["Human Review"]^)

> backend\app\api\v1\endpoints\documents.py echo from fastapi import APIRouter, File, UploadFile, status
>> backend\app\api\v1\endpoints\documents.py echo.
>> backend\app\api\v1\endpoints\documents.py echo router = APIRouter^(^)
>> backend\app\api\v1\endpoints\documents.py echo.
>> backend\app\api\v1\endpoints\documents.py echo @router.post^("", status_code=status.HTTP_202_ACCEPTED^)
>> backend\app\api\v1\endpoints\documents.py echo async def upload_document^(file: UploadFile = File^(...^)^):
>> backend\app\api\v1\endpoints\documents.py echo     # TODO: validate, virus-scan, store, create case and enqueue worker task.
>> backend\app\api\v1\endpoints\documents.py echo     return {"filename": file.filename, "status": "queued"}

> backend\app\api\v1\endpoints\verification.py echo from fastapi import APIRouter
>> backend\app\api\v1\endpoints\verification.py echo.
>> backend\app\api\v1\endpoints\verification.py echo router = APIRouter^(^)
>> backend\app\api\v1\endpoints\verification.py echo.
>> backend\app\api\v1\endpoints\verification.py echo @router.get^("/{case_id}"^)
>> backend\app\api\v1\endpoints\verification.py echo async def get_verification_result^(case_id: str^):
>> backend\app\api\v1\endpoints\verification.py echo     return {"case_id": case_id, "status": "processing"}

> backend\app\api\v1\endpoints\reviews.py echo from fastapi import APIRouter
>> backend\app\api\v1\endpoints\reviews.py echo.
>> backend\app\api\v1\endpoints\reviews.py echo router = APIRouter^(^)
>> backend\app\api\v1\endpoints\reviews.py echo.
>> backend\app\api\v1\endpoints\reviews.py echo @router.get^("/queue"^)
>> backend\app\api\v1\endpoints\reviews.py echo async def review_queue^(^):
>> backend\app\api\v1\endpoints\reviews.py echo     return {"items": []}

rem ------------------------------------------------------------
rem Configuration and worker starter
rem ------------------------------------------------------------
> backend\app\core\config.py echo from pydantic_settings import BaseSettings, SettingsConfigDict
>> backend\app\core\config.py echo.
>> backend\app\core\config.py echo.
>> backend\app\core\config.py echo class Settings^(BaseSettings^):
>> backend\app\core\config.py echo     model_config = SettingsConfigDict^(env_file=".env", extra="ignore"^)
>> backend\app\core\config.py echo.
>> backend\app\core\config.py echo     database_url: str = "postgresql+psycopg://app:app@localhost:5432/grd_document_verf"
>> backend\app\core\config.py echo     redis_url: str = "redis://localhost:6379/0"
>> backend\app\core\config.py echo     minio_endpoint: str = "http://localhost:9000"
>> backend\app\core\config.py echo     minio_access_key: str = "minioadmin"
>> backend\app\core\config.py echo     minio_secret_key: str = "minioadmin"
>> backend\app\core\config.py echo     secret_key: str = "change-me"
>> backend\app\core\config.py echo.
>> backend\app\core\config.py echo.
>> backend\app\core\config.py echo settings = Settings^(^)

> backend\app\workers\celery_app.py echo from celery import Celery
>> backend\app\workers\celery_app.py echo.
>> backend\app\workers\celery_app.py echo from app.core.config import settings
>> backend\app\workers\celery_app.py echo.
>> backend\app\workers\celery_app.py echo celery_app = Celery^(
>> backend\app\workers\celery_app.py echo     "grd_document_verf",
>> backend\app\workers\celery_app.py echo     broker=settings.redis_url,
>> backend\app\workers\celery_app.py echo     backend=settings.redis_url,
>> backend\app\workers\celery_app.py echo ^)
>> backend\app\workers\celery_app.py echo celery_app.autodiscover_tasks^(["app.workers"]^)

> backend\app\workers\tasks.py echo from app.workers.celery_app import celery_app
>> backend\app\workers\tasks.py echo.
>> backend\app\workers\tasks.py echo.
>> backend\app\workers\tasks.py echo @celery_app.task^(name="verify_document"^)
>> backend\app\workers\tasks.py echo def verify_document^(case_id: str, object_key: str^) -^> dict:
>> backend\app\workers\tasks.py echo     # Pipeline: OCR -^> extraction -^> consistency -^> tamper -^> duplicate -^> risk.
>> backend\app\workers\tasks.py echo     return {"case_id": case_id, "object_key": object_key, "status": "completed"}

rem ------------------------------------------------------------
rem Service placeholders
rem ------------------------------------------------------------
for %%F in (
    storage
    antivirus
    ocr
    document_classifier
    field_extractor
    layout_analyser
    consistency_checker
    image_tamper_detector
    duplicate_detector
    metadata_analyser
    risk_scoring
    human_review
    audit_service
) do type nul > backend\app\services\%%F.py

for %%F in (
    user
    document
    verification_case
    extracted_field
    fraud_signal
    review_decision
    audit_log
) do type nul > backend\app\models\%%F.py

for %%F in (
    auth
    document
    verification
    review
    common
) do type nul > backend\app\schemas\%%F.py

rem ------------------------------------------------------------
rem React frontend
rem ------------------------------------------------------------
echo Creating React TypeScript frontend...
call npm create vite@latest frontend -- --template react-ts
if errorlevel 1 (
    echo ERROR: Vite frontend creation failed.
    popd
    exit /b 1
)

pushd frontend
call npm install
call npm install axios @tanstack/react-query react-router-dom zustand react-dropzone react-hook-form zod
popd

mkdir frontend\src\api
mkdir frontend\src\components
mkdir frontend\src\components\common
mkdir frontend\src\features
mkdir frontend\src\features\auth
mkdir frontend\src\features\dashboard
mkdir frontend\src\features\documents
mkdir frontend\src\features\verification
mkdir frontend\src\features\human-review
mkdir frontend\src\features\reports
mkdir frontend\src\hooks
mkdir frontend\src\layouts
mkdir frontend\src\pages
mkdir frontend\src\routes
mkdir frontend\src\store
mkdir frontend\src\types
mkdir frontend\src\utils

> frontend\.env.example echo VITE_API_BASE_URL=http://localhost:8000/api/v1

rem ------------------------------------------------------------
rem Environment
rem ------------------------------------------------------------
> .env.example echo APP_ENV=development
>> .env.example echo SECRET_KEY=replace-with-a-long-random-secret
>> .env.example echo DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/grd_document_verf
>> .env.example echo REDIS_URL=redis://localhost:6379/0
>> .env.example echo MINIO_ENDPOINT=http://localhost:9000
>> .env.example echo MINIO_ACCESS_KEY=minioadmin
>> .env.example echo MINIO_SECRET_KEY=minioadmin
>> .env.example echo MINIO_BUCKET=grd-documents
>> .env.example echo MAX_UPLOAD_MB=25
>> .env.example echo HUMAN_REVIEW_THRESHOLD=0.70

rem ------------------------------------------------------------
rem Docker Compose infrastructure
rem ------------------------------------------------------------
> docker-compose.yml echo services:
>> docker-compose.yml echo   postgres:
>> docker-compose.yml echo     image: postgres:17
>> docker-compose.yml echo     environment:
>> docker-compose.yml echo       POSTGRES_DB: grd_document_verf
>> docker-compose.yml echo       POSTGRES_USER: app
>> docker-compose.yml echo       POSTGRES_PASSWORD: app
>> docker-compose.yml echo     ports:
>> docker-compose.yml echo       - "5432:5432"
>> docker-compose.yml echo     volumes:
>> docker-compose.yml echo       - postgres_data:/var/lib/postgresql/data
>> docker-compose.yml echo.
>> docker-compose.yml echo   redis:
>> docker-compose.yml echo     image: redis:8-alpine
>> docker-compose.yml echo     ports:
>> docker-compose.yml echo       - "6379:6379"
>> docker-compose.yml echo.
>> docker-compose.yml echo   minio:
>> docker-compose.yml echo     image: minio/minio:latest
>> docker-compose.yml echo     command: server /data --console-address ":9001"
>> docker-compose.yml echo     environment:
>> docker-compose.yml echo       MINIO_ROOT_USER: minioadmin
>> docker-compose.yml echo       MINIO_ROOT_PASSWORD: minioadmin
>> docker-compose.yml echo     ports:
>> docker-compose.yml echo       - "9000:9000"
>> docker-compose.yml echo       - "9001:9001"
>> docker-compose.yml echo     volumes:
>> docker-compose.yml echo       - minio_data:/data
>> docker-compose.yml echo.
>> docker-compose.yml echo volumes:
>> docker-compose.yml echo   postgres_data:
>> docker-compose.yml echo   minio_data:

rem ------------------------------------------------------------
rem Git ignore
rem ------------------------------------------------------------
> .gitignore echo # Python
>> .gitignore echo __pycache__/
>> .gitignore echo *.py[cod]
>> .gitignore echo backend/.venv/
>> .gitignore echo .pytest_cache/
>> .gitignore echo .ruff_cache/
>> .gitignore echo.
>> .gitignore echo # Node
>> .gitignore echo frontend/node_modules/
>> .gitignore echo frontend/dist/
>> .gitignore echo.
>> .gitignore echo # Environment and secrets
>> .gitignore echo .env
>> .gitignore echo backend/.env
>> .gitignore echo frontend/.env
>> .gitignore echo.
>> .gitignore echo # Local documents and models
>> .gitignore echo storage/uploads/*
>> .gitignore echo storage/processed/*
>> .gitignore echo storage/quarantine/*
>> .gitignore echo ml/datasets/*
>> .gitignore echo ml/models/*
>> .gitignore echo !storage/uploads/.gitkeep
>> .gitignore echo !storage/processed/.gitkeep
>> .gitignore echo !storage/quarantine/.gitkeep
>> .gitignore echo !ml/datasets/.gitkeep
>> .gitignore echo !ml/models/.gitkeep
>> .gitignore echo.
>> .gitignore echo # IDE and OS
>> .gitignore echo .vscode/
>> .gitignore echo .idea/
>> .gitignore echo .DS_Store
>> .gitignore echo Thumbs.db

type nul > storage\uploads\.gitkeep
type nul > storage\processed\.gitkeep
type nul > storage\quarantine\.gitkeep
type nul > ml\datasets\.gitkeep
type nul > ml\models\.gitkeep

rem ------------------------------------------------------------
rem Developer start scripts
rem ------------------------------------------------------------
> start-infra.bat echo @echo off
>> start-infra.bat echo docker compose up -d postgres redis minio

> start-backend.bat echo @echo off
>> start-backend.bat echo call backend\.venv\Scripts\activate.bat
>> start-backend.bat echo cd backend
>> start-backend.bat echo uvicorn app.main:app --reload --port 8000

> start-worker.bat echo @echo off
>> start-worker.bat echo call backend\.venv\Scripts\activate.bat
>> start-worker.bat echo cd backend
>> start-worker.bat echo celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=solo

> start-frontend.bat echo @echo off
>> start-frontend.bat echo cd frontend
>> start-frontend.bat echo call npm run dev

rem ------------------------------------------------------------
rem README
rem ------------------------------------------------------------
> README.md echo # GRD Document Verification
>> README.md echo.
>> README.md echo React dashboard plus FastAPI APIs, asynchronous document-processing workers,
>> README.md echo PostgreSQL, Redis and MinIO object storage.
>> README.md echo.
>> README.md echo ## Processing pipeline
>> README.md echo.
>> README.md echo 1. Upload and validate file
>> README.md echo 2. Malware scan and secure object storage
>> README.md echo 3. Document classification
>> README.md echo 4. OCR and layout extraction
>> README.md echo 5. Field validation and cross-document consistency
>> README.md echo 6. Image and metadata tamper checks
>> README.md echo 7. Duplicate and similarity detection
>> README.md echo 8. Fraud-signal aggregation and risk score
>> README.md echo 9. Human review when confidence is below threshold
>> README.md echo 10. Decision, explanation and audit trail
>> README.md echo.
>> README.md echo ## Run locally
>> README.md echo.
>> README.md echo 1. Copy `.env.example` to `backend\.env`.
>> README.md echo 2. Run `start-infra.bat`.
>> README.md echo 3. Run `start-backend.bat`.
>> README.md echo 4. Run `start-worker.bat`.
>> README.md echo 5. Run `start-frontend.bat`.
>> README.md echo.
>> README.md echo API docs: http://localhost:8000/docs
>> README.md echo Frontend: http://localhost:5173
>> README.md echo MinIO console: http://localhost:9001

rem ------------------------------------------------------------
rem Create Python virtual environment and install backend
rem ------------------------------------------------------------
echo Creating Python virtual environment...
%PYTHON_CMD% -m venv backend\.venv
if errorlevel 1 (
    echo ERROR: Python virtual environment creation failed.
    popd
    exit /b 1
)

call backend\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo WARNING: Some Python packages did not install successfully.
)
call deactivate

where git >nul 2>nul
if not errorlevel 1 (
    git init
)

echo.
echo ============================================================
echo Project created successfully.
echo Folder: %CD%
echo.
echo Next:
echo   1. copy .env.example backend\.env
echo   2. start-infra.bat
echo   3. start-backend.bat
echo   4. start-worker.bat
echo   5. start-frontend.bat
echo ============================================================
echo.

popd
endlocal
