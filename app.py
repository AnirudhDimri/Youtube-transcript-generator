import os
import logging
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from models import TranscriptRequest, TranscriptResponse
from index import (
    parse_youtube_url,
    clean_for_filename,
    process_and_save_transcript,
)

# Ensure logging is set up
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Create FastAPI app
app = FastAPI(
    title="YouTube Video Transcript Generator API",
    description="Generate and download transcripts for YouTube videos",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "YouTube Video Transcript Generator API",
        "version": "1.0.0",
        "endpoints": {
            "POST /transcript": "Generate transcript (returns JSON)",
            "POST /transcript/download": "Generate and download transcript as file",
            "GET /health": "Health check"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/transcript", response_model=TranscriptResponse)
async def generate_transcript(request: TranscriptRequest):
    """
    Generate transcript for a YouTube video
    
    - **video_url**: YouTube video URL (required)
    - **language**: Language code (default: "en")
    - **filename**: Custom filename (optional, defaults to video ID)
    """
    if not request.video_url:
        raise HTTPException(status_code=400, detail="Please provide a valid YouTube URL.")
    
    try:
        # Parse video details
        video_id = parse_youtube_url(request.video_url)
        final_filename = request.filename or clean_for_filename(video_id)
        temp_dir = tempfile.gettempdir()
        final_output_path = os.path.join(temp_dir, f"{final_filename}.md")

        # Generate transcript
        logging.info(f"Generating transcript for video ID: {video_id}")
        process_and_save_transcript(
            video_id=video_id,
            language=request.language,
            output_dir=temp_dir,
            filename=final_filename,
            verbose=False
        )

        # Read the generated transcript
        if not os.path.exists(final_output_path):
            raise HTTPException(
                status_code=500,
                detail=f"Transcript file could not be created at {final_output_path}"
            )

        with open(final_output_path, "r", encoding="utf-8") as file:
            transcript_content = file.read()

        return TranscriptResponse(
            success=True,
            video_id=video_id,
            filename=final_filename,
            transcript=transcript_content,
            message="Transcript generated successfully!"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Handle punctuation model unavailability
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logging.error(f"Error generating transcript: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.post("/transcript/download")
async def download_transcript(request: TranscriptRequest):
    """
    Generate and download transcript as a markdown file
    
    - **video_url**: YouTube video URL (required)
    - **language**: Language code (default: "en")
    - **filename**: Custom filename (optional, defaults to video ID)
    """
    if not request.video_url:
        raise HTTPException(status_code=400, detail="Please provide a valid YouTube URL.")
    
    try:
        # Parse video details
        video_id = parse_youtube_url(request.video_url)
        final_filename = request.filename or clean_for_filename(video_id)
        temp_dir = tempfile.gettempdir()
        final_output_path = os.path.join(temp_dir, f"{final_filename}.md")

        # Generate transcript
        logging.info(f"Generating transcript for video ID: {video_id}")
        process_and_save_transcript(
            video_id=video_id,
            language=request.language,
            output_dir=temp_dir,
            filename=final_filename,
            verbose=False
        )

        # Read the generated transcript
        if not os.path.exists(final_output_path):
            raise HTTPException(
                status_code=500,
                detail=f"Transcript file could not be created at {final_output_path}"
            )

        with open(final_output_path, "r", encoding="utf-8") as file:
            transcript_content = file.read()

        # Return as downloadable file
        return Response(
            content=transcript_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{final_filename}.md"'
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Handle punctuation model unavailability
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logging.error(f"Error generating transcript: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import logging as uvicorn_logging
    # Suppress invalid HTTP request warnings (usually from Swagger UI WebSocket attempts)
    uvicorn_logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
