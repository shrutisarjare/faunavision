import { useRef, useState } from "react";
import { UploadCloud, Mic, Video, Music, Sparkles, X } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Identify = () => {

  const navigate = useNavigate();

  const imageInputRef = useRef(null);
  const videoInputRef = useRef(null);
  const audioInputRef = useRef(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const abortControllerRef = useRef(null);

  const [imageFile, setImageFile] = useState(null);
  const [videoFile, setVideoFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [description, setDescription] = useState("");
  const [isRecording, setIsRecording] = useState(false);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  // ================= RESET =================
  const resetAll = () => {
    setImageFile(null);
    setVideoFile(null);
    setAudioFile(null);
    setResult(null);
    setError("");
    setLoading(false);
  };

  // ================= IMAGE =================
  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      resetAll();
      setImageFile(file);
    }
  };

  // ================= VIDEO =================
  const handleVideoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      resetAll();
      setVideoFile(file);
    }
  };

  // ================= AUDIO UPLOAD =================
  const handleAudioUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      resetAll();
      setAudioFile(file);
    }
  };

  // ================= LIVE RECORD =================
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(audioChunksRef.current, {
          type: "audio/webm",
        });
        const file = new File([blob], "recorded.webm");
        resetAll();
        setAudioFile(file);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch {
      setError("Microphone permission denied.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setAudioFile(null);
  };

  // ================= IDENTIFY =================
  const handleIdentify = async () => {

    setLoading(true);
    setError("");
    setResult(null);

    try {

      // TEXT INPUT
      if (description.trim() !== "") {

        const response = await fetch(
          `${import.meta.env.VITE_ML_API_URL || 'http://localhost:8000'}/identify-text`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              text: description
            })
          }
        );

        const data = await response.json();
        setResult(data.species);
        navigate(`/detect/${data.species.toLowerCase()}`);
      }

      // IMAGE INPUT
      else if (imageFile) {

        const formData = new FormData();
        formData.append("file", imageFile);

        const response = await fetch(
          `${import.meta.env.VITE_ML_API_URL || 'http://localhost:8000'}/identify-image`,
          {
            method: "POST",
            body: formData
          }
        );

        const data = await response.json();

        setResult(data.species);

        // AUTO NAVIGATION
        navigate(`/detect/${data.species.toLowerCase()}`);
      }

      // VIDEO INPUT ✅ UPDATED
      else if (videoFile) {

        const formData = new FormData();
        formData.append("file", videoFile);

        const response = await fetch(
          `${import.meta.env.VITE_ML_API_URL || 'http://localhost:8000'}/identify-video`,
          {
            method: "POST",
            body: formData
          }
        );

        const data = await response.json();

        setResult(data.species);

        // 🔥 ADDED (same as image)
        navigate(`/detect/${data.species.toLowerCase()}`);
      }

      // AUDIO INPUT
      else if (audioFile) {

        const formData = new FormData();
        formData.append("file", audioFile);

        const response = await fetch(
          `${import.meta.env.VITE_ML_API_URL || 'http://localhost:8000'}/identify-audio`,
          {
            method: "POST",
            body: formData
          }
        );

        const data = await response.json();
        setResult(data.species);
        navigate(`/detect/${data.species.toLowerCase()}`);
      }

    } catch {
      setError("Identification failed");
    }

    setLoading(false);
  };

  const cancelProcessing = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setLoading(false);
  };

  const hasInput =
    imageFile || videoFile || audioFile || description.trim() !== "";

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-cover bg-center px-4"
      style={{ backgroundImage: "url('/hero.png')" }}
    >
      <div className="bg-white/85 backdrop-blur-md rounded-2xl shadow-2xl p-6 w-full max-w-md text-center">

        <h1 className="text-2xl font-semibold text-green-700 flex items-center justify-center gap-2 mb-4">
          <Sparkles size={20} />
          Identify a Species
        </h1>

        <input type="file" accept="image/*" ref={imageInputRef} onChange={handleImageUpload} className="hidden" />
        <input type="file" accept="video/*" ref={videoInputRef} onChange={handleVideoUpload} className="hidden" />
        <input type="file" accept="audio/*" ref={audioInputRef} onChange={handleAudioUpload} className="hidden" />

        <button onClick={() => imageInputRef.current.click()} className="w-full bg-green-100 hover:bg-green-200 text-green-800 py-2 rounded-lg mb-2">
          Upload Image
        </button>

        <button onClick={() => videoInputRef.current.click()} className="w-full bg-green-100 hover:bg-green-200 text-green-800 py-2 rounded-lg mb-2">
          Upload Video
        </button>

        <button onClick={() => audioInputRef.current.click()} className="w-full bg-green-100 hover:bg-green-200 text-green-800 py-2 rounded-lg mb-3">
          Upload Audio
        </button>

        <div className="flex items-center gap-2 mb-3">
          <input
            type="text"
            placeholder="Describe the species..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2"
          />

         
        </div>

        {imageFile && <p className="text-sm text-green-800">🖼 {imageFile.name}</p>}
        {videoFile && <p className="text-sm text-green-800">🎥 {videoFile.name}</p>}
        {audioFile && <p className="text-sm text-green-800">🎧 {audioFile.name}</p>}

        <button
          onClick={handleIdentify}
          disabled={!hasInput || loading}
          className={`w-full py-3 rounded-lg font-semibold mt-3 ${
            hasInput ? "bg-green-700 text-white" : "bg-green-200 text-green-500"
          }`}
        >
          {loading ? "Processing..." : "Identify"}
        </button>

        {loading && (
          <button onClick={cancelProcessing} className="mt-2 text-red-600 text-sm">
            Cancel Processing
          </button>
        )}

        {result && (
          <div className="mt-4 p-3 bg-green-50 border border-green-300 rounded-lg">

            🐾 Detected: <b>{result}</b>

            <div className="mt-3">
              <button
               onClick={() => navigate(`/detect/${result.toLowerCase()}`)}
                className="bg-green-700 text-white px-3 py-1 rounded"
              >
                View About
              </button>
            </div>

          </div>
        )}

        {error && <p className="mt-3 text-red-600 text-sm">{error}</p>}
      </div>
    </div>
  );
};

export default Identify;