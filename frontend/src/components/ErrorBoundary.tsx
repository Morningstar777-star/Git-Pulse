import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught application render error:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-6">
          <div className="max-w-md w-full p-6 rounded-2xl bg-slate-800 border border-slate-700 shadow-2xl text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold">Something went wrong</h2>
            <p className="text-xs text-slate-400 font-mono">
              {this.state.error?.message || "An unexpected error occurred while rendering the dashboard."}
            </p>
            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono font-medium transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Reload Dashboard</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
