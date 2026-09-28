import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { bindBackButton } from "../lib/telegram.js";

/** Shows Telegram's native back button on sub-pages. */
export default function useBackButton(to = -1) {
  const navigate = useNavigate();
  useEffect(() => bindBackButton(() => navigate(to)), [navigate, to]);
}
