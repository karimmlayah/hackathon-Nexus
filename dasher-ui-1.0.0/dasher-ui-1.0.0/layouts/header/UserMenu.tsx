import React, { useEffect, useState } from "react";
import { Dropdown, Image } from "react-bootstrap";
import Link from "next/link";
import { IconLogin2 } from "@tabler/icons-react";
import { useRouter } from "next/navigation";

//import routes files
import { UserMenuItem } from "routes/HeaderRoute";

//import custom components
import { Avatar } from "components/common/Avatar";
import { getAssetPath } from "helper/assetPath";

interface UserToggleProps {
  children?: React.ReactNode;
  onClick?: () => void;
}
const CustomToggle = React.forwardRef<HTMLAnchorElement, UserToggleProps>(
  ({ children, onClick }, ref) => (
    <Link ref={ref} href="#" onClick={onClick}>
      {children}
    </Link>
  )
);

const UserMenu = () => {
  const router = useRouter();
  const [user, setUser] = useState<{ name: string; email: string; avatar?: string } | null>(null);

  useEffect(() => {
    // Check for real token/user in localStorage
    const storedUser = localStorage.getItem("finfit_user");
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    } else {
      // Fallback or guest
      setUser({
        name: "Admin User",
        email: "admin@finfit.com"
      });
    }
  }, []);

  const handleLogout = (e: React.MouseEvent) => {
    e.preventDefault();
    localStorage.removeItem("finfit_token");
    localStorage.removeItem("finfit_user");
    // Redirect to the static sign-in page on the marketplace server
    window.location.href = "http://localhost:8000/signin.html";
  };

  // Helper to get initials
  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <Dropdown>
      <Dropdown.Toggle as={CustomToggle}>
        <div
          className="rounded-circle d-flex align-items-center justify-content-center bg-primary text-white fw-bold"
          style={{ width: "32px", height: "32px", fontSize: "14px" }}
        >
          {user ? getInitials(user.name) : "GU"}
        </div>
      </Dropdown.Toggle>
      <Dropdown.Menu align="end" className="p-0 dropdown-menu-md">
        <div className="d-flex gap-3 align-items-center border-dashed border-bottom px-4 py-4">
          <div
            className="rounded-circle d-flex align-items-center justify-content-center bg-primary text-white fw-bold display-6"
            style={{ width: "48px", height: "48px", fontSize: "20px" }}
          >
            {user ? getInitials(user.name) : "GU"}
          </div>
          <div>
            <h4 className="mb-0 fs-5">{user ? user.name : "Guest User"}</h4>
            <p className="mb-0 text-secondary small">{user ? user.email : "Not logged in"}</p>
          </div>
        </div>
        <div className="p-3 d-flex flex-column gap-1">
          {UserMenuItem.map((item) => (
            <Dropdown.Item
              key={item.id}
              className="d-flex align-items-center gap-2"
              href={item.link || "#"}
            >
              <span>{item.icon}</span>
              <span>{item.title}</span>
            </Dropdown.Item>
          ))}
        </div>
        <div className="border-dashed border-top mb-4 pt-4 px-6">
          <Link
            href="#"
            onClick={handleLogout}
            className="text-secondary d-flex align-items-center gap-2"
          >
            <span>
              <IconLogin2 size={20} strokeWidth={1.5} />
            </span>
            <span>Logout</span>
          </Link>
        </div>
      </Dropdown.Menu>
    </Dropdown>
  );
};

export default UserMenu;
