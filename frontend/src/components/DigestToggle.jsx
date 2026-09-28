import { BarChart3 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { useApp } from "../state/AppContext.jsx";
import OptionRow from "./pro/OptionRow.jsx";
import { ListGroup } from "./ui/List.jsx";

export default function DigestToggle() {
  const { toast } = useApp();
  const [me, setMe] = useState(null);

  useEffect(() => {
    api
      .getMe()
      .then(setMe)
      .catch(() => {});
  }, []);

  if (!me) return null;

  async function toggle(weeklyDigest) {
    setMe({ ...me, weekly_digest: weeklyDigest });
    try {
      setMe(await api.updateMe({ weekly_digest: weeklyDigest }));
    } catch (err) {
      setMe(me);
      toast(err.message, "danger");
    }
  }

  return (
    <ListGroup title="Уведомления в боте">
      <OptionRow
        icon={BarChart3}
        title="Сводка за неделю"
        subtitle="По понедельникам: ответы, новые обращения и доставляемость рассылок"
        checked={me.weekly_digest}
        onChange={toggle}
        proOnly
      />
    </ListGroup>
  );
}
