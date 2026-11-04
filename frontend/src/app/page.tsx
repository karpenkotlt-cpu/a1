import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-zinc-50">
      <h1 className="text-3xl font-semibold">
        Smart Quote &amp; CAM-Costing System
      </h1>
      <p className="max-w-md text-center text-zinc-600">
        Быстрая оценка стоимости механообработки и точная технологическая
        калькуляция
      </p>
      <div className="flex gap-4">
        <Link
          href="/constructor"
          className="rounded-md bg-zinc-900 px-6 py-2.5 text-sm font-medium text-white hover:bg-zinc-700"
        >
          2.5D-конструктор
        </Link>
        <Link
          href="/quotes"
          className="rounded-md border px-6 py-2.5 text-sm font-medium hover:bg-zinc-100"
        >
          Расчёты
        </Link>
        <Link
          href="/materials"
          className="rounded-md border px-6 py-2.5 text-sm font-medium hover:bg-zinc-100"
        >
          Материалы
        </Link>
        <Link
          href="/tools"
          className="rounded-md border px-6 py-2.5 text-sm font-medium hover:bg-zinc-100"
        >
          Инструмент
        </Link>
      </div>
    </div>
  );
}
