import { useNavigate } from "react-router-dom";

import StaffLoginPage from "../LoginPage";
import { useSessionStore } from "../shared/store";
import type { StaffLoginResponse } from "../shared/types";

export default function LoginPage() {
  const navigate = useNavigate();
  const setStaff = useSessionStore((state) => state.setStaff);

  function handleSuccess(data: StaffLoginResponse) {
    setStaff(data.role, data.branch_id, data.user_id);
    navigate("/kitchen/board");
  }

  return <StaffLoginPage role="kitchen" onSuccess={handleSuccess} />;
}
