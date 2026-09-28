import { KeyRound, QrCode } from "lucide-react";
import { useCallback, useState } from "react";
import { useApp } from "../../state/AppContext.jsx";
import Segmented from "../ui/Segmented.jsx";
import Sheet from "../ui/Sheet.jsx";
import CodeLogin from "./CodeLogin.jsx";
import QrLogin from "./QrLogin.jsx";

export default function AddAccountSheet({ open, onClose }) {
  const { upsertAccount, toast } = useApp();
  const [mode, setMode] = useState("code");

  const handleSuccess = useCallback(
    (account) => {
      upsertAccount(account);
      toast("Аккаунт подключён — автопилот включён");
      onClose();
    },
    [upsertAccount, toast, onClose],
  );

  return (
    <Sheet open={open} onClose={onClose} title="Подключить аккаунт">
      <div className="space-y-5 pt-1">
        <Segmented
          value={mode}
          onChange={setMode}
          options={[
            { value: "code", label: "По номеру", icon: KeyRound },
            { value: "qr", label: "По QR-коду", icon: QrCode },
          ]}
        />
        {mode === "code" ? (
          <CodeLogin onSuccess={handleSuccess} />
        ) : (
          <QrLogin onSuccess={handleSuccess} />
        )}
      </div>
    </Sheet>
  );
}
