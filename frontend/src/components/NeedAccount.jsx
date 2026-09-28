import { Plane } from "lucide-react";
import { useNavigate } from "react-router-dom";
import PageTitle from "./PageTitle.jsx";
import Button from "./ui/Button.jsx";
import { EmptyState } from "./ui/Feedback.jsx";

export default function NeedAccount({ title }) {
  const navigate = useNavigate();
  return (
    <div className="space-y-4 p-4">
      <PageTitle title={title} />
      <EmptyState
        icon={Plane}
        title="Сначала подключите аккаунт"
        text="Автопилот работает от имени вашего аккаунта Telegram."
        action={<Button onClick={() => navigate("/")}>Подключить</Button>}
      />
    </div>
  );
}
