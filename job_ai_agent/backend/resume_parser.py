import fitz 
import ollama
import json

class ResumeParser:
    def parse(self, file_bytes: bytes):
        try:
            # 1. Extract raw text from PDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            raw_text = ""
            for page in doc:
                raw_text += page.get_text()
            doc.close()

            # 2. Ask Ollama to structure the data
            prompt = f"""
            Extract the following information from the resume text below:
            1. Skills (as a list of strings)
            2. Professional Experience (Number of years in total)

            Return the response strictly as a JSON object with keys "skills" and "experience".
            
            Resume Text:
            {raw_text[:4000]} 
            """

            response = ollama.generate(model="llama3.2:3b", prompt=prompt, format="json")
            
            # 3. Parse the JSON response
            parsed_data = json.loads(response['response'])
            
            return {
                "skills": parsed_data.get("skills", []),
                "experience": parsed_data.get("experience", "No experience found")
            }

        except Exception as e:
            print(f"Ollama Parsing Error: {e}")
            # Fallback if Ollama fails
            return {"skills": ["Error processing"], "experience": "Error"}

parser_service = ResumeParser()