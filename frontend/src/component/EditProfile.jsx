import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { User } from "lucide-react";

const EditProfile = () => {
  const user = JSON.parse(localStorage.getItem("user"));
  const navigate = useNavigate();

  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    try {
      // 🔴 Check user
      if (!user) {
        alert("Please login again");
        navigate("/login");
        return;
      }

      // ✅ FIX: support both id and _id
      const userId = user._id || user.id;

      if (!userId) {
        alert("Session expired. Please login again.");
        navigate("/login");
        return;
      }

      setLoading(true);

      const response = await fetch(
        `${import.meta.env.VITE_ML_API_URL || 'http://localhost:8000'}/update-profile`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            _id: userId,
            name,
            email,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Update failed");
      }

      // ✅ Update localStorage
      const updatedUser = {
        ...user,
        name,
        email,
      };

      localStorage.setItem("user", JSON.stringify(updatedUser));

      alert("Profile updated successfully!");
      navigate("/profile");

    } catch (err) {
      console.error("Update error:", err);
      alert(err.message || "Update failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-cover bg-center relative px-4"
      style={{
        backgroundImage:
          "url('https://images.unsplash.com/photo-1500530855697-b586d89ba3ee')",
      }}
    >
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/60"></div>

      {/* Card */}
      <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 shadow-2xl p-8 rounded-3xl w-full max-w-md text-center text-white">

        {/* Avatar */}
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center text-green-700">
          <User size={28} />
        </div>

        {/* Title */}
        <h1 className="text-2xl font-bold mb-6">Edit Profile</h1>

        {/* Name */}
        <input
          type="text"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full mb-4 px-4 py-2 rounded-xl bg-white/80 text-black outline-none"
        />

        {/* Email */}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-6 px-4 py-2 rounded-xl bg-white/80 text-black outline-none"
        />

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={loading}
          className="w-full bg-gradient-to-r from-green-500 to-green-600 py-3 rounded-xl font-semibold 
                     hover:scale-105 hover:shadow-lg transition-all duration-300 disabled:opacity-50"
        >
          {loading ? "Saving..." : "Save Changes"}
        </button>

      </div>
    </div>
  );
};

export default EditProfile;