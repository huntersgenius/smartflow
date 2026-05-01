import { ShoppingBag } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { money } from "../../shared/format";
import BottomSheet from "../../shared/components/BottomSheet";
import { useCart } from "../hooks/useCart";

export default function CartSheet() {
  const navigate = useNavigate();
  const { tableCode } = useParams();
  const { itemCount, total, estimatedTime } = useCart();

  if (itemCount === 0) return null;

  return (
    <BottomSheet>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-sf-dark">
            {itemCount} ta mahsulot <span className="text-sf-green">{money(total)}</span>
          </p>
          <p className="mt-1 text-sm font-semibold text-sf-dark">{estimatedTime.label}</p>
          <p className="text-xs text-slate-500">Navbatga qarab o'zgaradi</p>
        </div>
        <button
          className="flex shrink-0 items-center gap-2 rounded-lg bg-sf-green px-4 py-3 text-sm font-bold text-white"
          onClick={() => navigate(`/t/${tableCode}/cart`)}
        >
          <ShoppingBag size={17} />
          Savatni ko'rish
        </button>
      </div>
    </BottomSheet>
  );
}
