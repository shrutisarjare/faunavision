const express = require("express");
const multer = require("multer");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

const router = express.Router();

// ------------------------------
// Configure Multer (file upload)
// ------------------------------
const upload = multer({
  dest: "/tmp/", // temporary upload folder
});

// ------------------------------
// POST /api/audio/predict
// ------------------------------
router.post("/predict", upload.single("audio"), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ message: "No audio file uploaded" });
  }

  const filePath = req.file.path;

  // Call Python script
  const pythonProcess = spawn("python", [
    "ml/predict.py",
    filePath,
  ]);

  let result = "";

  pythonProcess.stdout.on("data", (data) => {
    result += data.toString();
  });

  pythonProcess.stderr.on("data", (data) => {
    console.error("Python Error:", data.toString());
  });

  pythonProcess.on("close", (code) => {
    // Delete uploaded file after prediction
    fs.unlinkSync(filePath);

    if (code !== 0) {
      return res.status(500).json({ message: "Prediction failed" });
    }

    return res.json({
      prediction: result.trim(),
    });
  });
});

module.exports = router;