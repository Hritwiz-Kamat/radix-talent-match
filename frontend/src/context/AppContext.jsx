
import { createContext, useContext, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [currentCandidate, setCurrentCandidate] = useState(null);
  const [currentJD, setCurrentJD] = useState(null);

  return (
    <AppContext.Provider
      value={{
        currentCandidate,
        setCurrentCandidate,
        currentJD,
        setCurrentJD,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);

  if (!context) {
    throw new Error("useAppContext must be used inside AppProvider");
  }

  return context;
}
