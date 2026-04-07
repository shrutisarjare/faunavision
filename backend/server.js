const express = require("express");
const dotenv = require("dotenv");
const cors = require("cors");
const connectDB = require("./config/db");
const textRoutes = require("./routes/textIdentify");
// Routes
const authRoutes = require("./routes/auth");
const contactRoutes = require("./routes/contact");
const audioRoutes = require("./routes/audio");
const identifyRoutes = require("./routes/identify");
dotenv.config();
connectDB();

const app = express();

// Enable CORS
app.use(
  cors({
    origin: process.env.FRONTEND_URL || "http://localhost:5173",
    credentials: true,
  })
);

// Parse JSON body
app.use(express.json());

// Routes
app.use("/api/auth", authRoutes);
app.use("/api/contact", contactRoutes);
app.use("/api/audio", audioRoutes);
app.use("/api/text", textRoutes);
app.use("/api/identify", identifyRoutes);
// Port
const PORT = process.env.PORT || 5001;

if (process.env.NODE_ENV !== "production") {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

module.exports = app;
