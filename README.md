# News Content Management API

A robust backend REST API built using **FastAPI**, **SQLAlchemy**, and **SQLite** to manage posts for a social media news page, integrated with **Groq's LPU Inference API** for AI-driven news content summarization.

---

## Features

- **CRUD Operations**: Full CRUD support for news posts.
- **Advanced Filtering & Search**: List posts with multi-parameter filters (by category, status) and full-text keyword search in both title and content.
- **Pagination & Sorting**: Support for `skip`/`limit` pagination and custom sorting (`created_at` or `views`).
- **Dashboard Statistics**: Dynamic metrics showing total, draft, published, and archived post counts, total view count, and the most viewed post.
- **View Tracking**: Incremental tracking of post view counts.
- **Groq AI Summary Generation**: Send a post's content to Groq's API (`llama-3.1-8b-instant`) to generate and store a concise one-sentence summary.
- **Robust Fallback**: Includes a fallback mode that truncates content in case of network errors or missing API keys, preventing the app from crashing.
- **Secure Write Actions**: API-key authentication header required (`X-API-Key`) for create, update, and delete endpoints.

---

## Technical Stack

- **Framework**: FastAPI (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Simple API-key header validation
- **AI Engine**: Groq API (`llama-3.1-8b-instant`)
- **Web Server**: Uvicorn

---

## Installation & Setup

Follow these steps to set up and run the project locally.

### 1. Clone or Open the Project
Ensure you are in the project's root directory:
```bash
cd c:/Users/Acer/Videos/tghotnewsapi
```

### 2. Create and Activate the Virtual Environment
Using Python's built-in `venv` module:

**On Windows (Command Prompt/PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install all required Python packages:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
1. Copy the template from `.env.example` to a new `.env` file in the `app` directory:
   ```bash
   cp .env.example app/.env
   ```
2. Open `app/.env` and replace the placeholder keys with your actual values:
   ```env
   GROQ_API_KEY=gsk_...
   API_KEY=secret-api-key
   ```
   *Note: If no `.env` file is present or keys are empty, the application will default to standard fallback operations without crashing.*

### 5. Run the Server
Launch the development server using Uvicorn:
```bash
uvicorn app.main:app --reload
```
Once started, the API will be available at: **`http://127.0.0.1:8000`**
Interactive Swagger Documentation can be accessed at: **`http://127.0.0.1:8000/docs`**

---

## API Endpoints List

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| **POST** | `/posts` | Create a new news post | Yes (`X-API-Key`) |
| **GET** | `/posts` | Retrieve all posts (supports filters, search, pagination, and sorting) | No |
| **GET** | `/posts/{post_id}` | Get details of a single post | No |
| **PUT** | `/posts/{post_id}` | Complete update of a post | Yes (`X-API-Key`) |
| **PATCH** | `/posts/{post_id}` | Partial update of a post | Yes (`X-API-Key`) |
| **DELETE** | `/posts/{post_id}` | Delete a post | Yes (`X-API-Key`) |
| **POST** | `/posts/{post_id}/view` | Increment view count by 1 | No |
| **POST** | `/posts/{post_id}/summarize` | Trigger Groq AI summary generation | No |
| **GET** | `/dashboard/stats` | Retrieve aggregated analytics and dashboard stats | No |

---

## Example Requests (cURL)

### 1. Create a News Post
```bash
curl -X POST "http://127.0.0.1:8000/posts" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: secret-api-key" \
     -d '{
       "title": "FastAPI Release 0.110.0",
       "content": "FastAPI continues to dominate the Python ecosystem with rapid asynchronous performance and automated OpenAPI specifications.",
       "category": "Tech",
       "status": "draft"
     }'
```

### 2. List Posts with Filtering, Sorting and Pagination
```bash
curl -X GET "http://127.0.0.1:8000/posts?category=Tech&status=draft&search=FastAPI&sort_by=views&order=desc&skip=0&limit=10"
```

### 3. Increment Post Views
```bash
curl -X POST "http://127.0.0.1:8000/posts/1/view"
```

### 4. Update Post (PUT)
```bash
curl -X PUT "http://127.0.0.1:8000/posts/1" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: secret-api-key" \
     -d '{
       "title": "FastAPI Release 0.111.0",
       "content": "Updated content describing the new releases and asynchronous database improvements in FastAPI.",
       "category": "Technology",
       "status": "published"
     }'
```

### 5. Generate AI Summary (Groq llama-3.1-8b-instant)
```bash
curl -X POST "http://127.0.0.1:8000/posts/1/summarize"
```

### 6. Retrieve Dashboard Analytics
```bash
curl -X GET "http://127.0.0.1:8000/dashboard/stats"
```

---

## Assumptions & Design Choices

1. **AI Key Fallback Strategy**: If `GROQ_API_KEY` is not present, is invalid, or the Groq server is offline, the endpoint `/posts/{post_id}/summarize` will fall back to returning the first 100 characters of the content appended with `"..."`. This keeps the API reliable and testable without active third-party API configurations.
2. **Database Initialization**: The SQLite database engine (`news.db`) is automatically initialized, and tables are created dynamically on application startup via FastAPI's modern `lifespan` handler. No manual migration tool is required for initial setup.
3. **Authentication Strategy**: For demo simplicity, API security uses a static `X-API-Key` header with a configurable fallback value of `"secret-api-key"` if the environment variable `API_KEY` is not set.
4. **Duplicate Title Prevention**: To maintain data integrity, creating or modifying a post's title is checked against all existing titles in the database. If a conflict is found, a `400 Bad Request` is raised.
