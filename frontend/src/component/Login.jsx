import { Link, useNavigate, useLocation } from "react-router-dom";
import { Home } from "lucide-react";
import { useState } from "react";
import axios from "axios";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const [role, setRole] = useState("user");

  const handleLogin = async () => {
    setError("");

    try {
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL || 'http://localhost:5001'}/api/auth/login`,
        { email, password }
      );

      // ✅ Save user info
      localStorage.setItem("token", res.data.token);
      localStorage.setItem("user", JSON.stringify(res.data.user));

      // ✅ Redirect to home
     const user = res.data.user;

// 👑 Admin → go to dashboard
if (user.role === "admin") {
  navigate("/AdminDashboard");
} else {
  // 👤 User → go back to previous page OR home
  const redirectPath = location.state?.from || "/";
  navigate(redirectPath);
}

    } catch (err) {
      if (err.response?.data?.message === "User not found. Please register first.") {
        setError("No account found. Please register first.");
      } else {
        setError(err.response?.data?.message || "Login failed");
      }
    }
  };

  return (
    <div className="min-h-screen bg-[url('/hero.png')] bg-cover bg-center flex items-center justify-center px-4">
      <div className="relative bg-white/90 backdrop-blur p-6 sm:p-8 md:p-10 rounded-2xl shadow-xl w-full max-w-sm">

        {/* Home Icon */}
        <Link to="/" className="absolute top-4 right-4 text-green-700">
          <Home />
        </Link>

        <h1 className="text-3xl font-bold text-green-700 text-center mb-2">
          Welcome Back 🌿
        </h1>

        <p className="text-center text-gray-500 mb-4">
          Login to continue
        </p>

        {error && (
          <p className="text-red-600 text-center mb-3 font-medium">
            {error}
          </p>
        )}

        <input
          type="email"
          placeholder="Email"
          className="w-full p-3 mb-4 border rounded-lg"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          type="password"
          placeholder="Password"
          className="w-full p-3 mb-6 border rounded-lg"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <select
  className="w-full p-3 mb-6 border rounded-lg"
  value={role}
  onChange={(e) => setRole(e.target.value)}
>
  <option value="user">User</option>
  <option value="admin">Admin</option>
</select>

        <button
          type="button"
          onClick={handleLogin}
          className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg text-lg transition"
        >
          Login
        </button>

        <p className="text-center mt-4 text-gray-600">
          Don’t have an account?{" "}
          <Link to="/register" className="text-green-700 font-semibold">
            Register
          </Link>
        </p>

      </div>
    </div>
  );
}
