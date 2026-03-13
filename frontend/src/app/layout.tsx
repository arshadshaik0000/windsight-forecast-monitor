import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '@/components/ThemeProvider';

export const metadata: Metadata = {
  title: 'WindSight — UK Wind Power Forecast Monitor',
  description:
    'Real-time monitoring dashboard for UK wind generation forecasts vs actuals. Visualize forecast accuracy, error metrics, and wind reliability.',
  keywords: ['wind power', 'forecast', 'UK energy', 'BMRS', 'monitoring'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
