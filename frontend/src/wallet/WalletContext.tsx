import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { CDPHooksProvider, useCurrentUser, useEvmAddress, useSignInWithOAuth, useSignOut, useX402 } from '@coinbase/cdp-hooks';

export type WalletOAuthProvider = 'google' | 'apple' | 'x';

type WalletFetch = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

interface WalletSession {
  configured: boolean;
  projectId: string | null;
  useMock: boolean;
  signedIn: boolean;
  address: string | null;
  signingIn: boolean;
  signingOut: boolean;
  signIn: (provider?: WalletOAuthProvider) => Promise<void>;
  signOut: () => Promise<void>;
  fetchWithPayment: WalletFetch;
  configureWallet: (config: { projectId: string; useMock: boolean }) => void;
  clearWalletConfig: () => void;
}

const WalletContext = createContext<WalletSession | null>(null);
const PROJECT_ID_STORAGE_KEY = 'pricer.cdp.projectId';
const USE_MOCK_STORAGE_KEY = 'pricer.cdp.useMock';
const DEFAULT_PROJECT_ID = import.meta.env.VITE_CDP_PROJECT_ID?.trim() ?? '';
const DEFAULT_USE_MOCK = import.meta.env.VITE_CDP_USE_MOCK === 'true';
const MOCK_ADDRESS = '0x00000000000000000000000000000000c0ffee00';

const defaultSession: WalletSession = {
  configured: DEFAULT_USE_MOCK || Boolean(DEFAULT_PROJECT_ID),
  projectId: DEFAULT_PROJECT_ID || null,
  useMock: DEFAULT_USE_MOCK,
  signedIn: false,
  address: null,
  signingIn: false,
  signingOut: false,
  signIn: async () => {
    throw new Error('Wallet sign-in is not configured. Set up the wallet in the UI first.');
  },
  signOut: async () => {},
  fetchWithPayment: fetch as WalletFetch,
  configureWallet: () => {},
  clearWalletConfig: () => {},
};

function abbreviate(address: string) {
  return `${address.slice(0, 6)}…${address.slice(-4)}`;
}

function createMockSession(sessionBase: WalletSession, setProjectId: (value: string) => void, setUseMock: (value: boolean) => void): WalletSession {
  return {
    ...sessionBase,
    configured: true,
    projectId: sessionBase.projectId,
    useMock: true,
    signedIn: true,
    address: MOCK_ADDRESS,
    signingIn: false,
    signingOut: false,
    signIn: async () => {},
    signOut: async () => {},
    fetchWithPayment: fetch as WalletFetch,
    configureWallet: ({ projectId: nextProjectId, useMock: nextUseMock }) => {
      const trimmed = nextProjectId.trim();
      if (typeof window !== 'undefined') {
        if (trimmed) {
          window.localStorage.setItem(PROJECT_ID_STORAGE_KEY, trimmed);
        } else {
          window.localStorage.removeItem(PROJECT_ID_STORAGE_KEY);
        }
        window.localStorage.setItem(USE_MOCK_STORAGE_KEY, String(nextUseMock));
      }
      setProjectId(trimmed);
      setUseMock(nextUseMock);
    },
    clearWalletConfig: () => {
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(PROJECT_ID_STORAGE_KEY);
        window.localStorage.removeItem(USE_MOCK_STORAGE_KEY);
      }
      setProjectId('');
      setUseMock(false);
    },
  };
}

function CdpWalletBridge({ children, sessionBase }: { children: ReactNode; sessionBase: WalletSession }) {
  const { currentUser } = useCurrentUser();
  const { evmAddress } = useEvmAddress();
  const { signInWithOAuth } = useSignInWithOAuth();
  const { signOut: cdpSignOut } = useSignOut();
  const { fetchWithPayment: rawFetchWithPayment } = useX402({
    address: evmAddress ?? undefined,
  });

  const [signingIn, setSigningIn] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  const value = useMemo<WalletSession>(() => ({
    ...sessionBase,
    configured: true,
    projectId: sessionBase.projectId,
    useMock: sessionBase.useMock,
    signedIn: Boolean(currentUser && evmAddress),
    address: evmAddress ?? null,
    signingIn,
    signingOut,
    signIn: async (provider: WalletOAuthProvider = 'google') => {
      setSigningIn(true);
      try {
        await signInWithOAuth(provider);
      } finally {
        setSigningIn(false);
      }
    },
    signOut: async () => {
      setSigningOut(true);
      try {
        await cdpSignOut();
      } finally {
        setSigningOut(false);
      }
    },
    fetchWithPayment: rawFetchWithPayment as WalletFetch,
  }), [cdpSignOut, currentUser, evmAddress, rawFetchWithPayment, sessionBase, signInWithOAuth, signingIn, signingOut]);

  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>;
}

export function WalletProvider({ children }: { children: ReactNode }) {
  const [projectId, setProjectId] = useState(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_PROJECT_ID;
    }
    return window.localStorage.getItem(PROJECT_ID_STORAGE_KEY)?.trim() || DEFAULT_PROJECT_ID;
  });
  const [useMock, setUseMock] = useState(() => {
    if (typeof window === 'undefined') {
      return DEFAULT_USE_MOCK;
    }
    const stored = window.localStorage.getItem(USE_MOCK_STORAGE_KEY);
    return stored == null ? DEFAULT_USE_MOCK : stored === 'true';
  });

  const baseSession = useMemo<WalletSession>(() => ({
    configured: useMock || Boolean(projectId),
    projectId: projectId || null,
    useMock,
    signedIn: false,
    address: null,
    signingIn: false,
    signingOut: false,
    signIn: async () => {
      throw new Error('Wallet sign-in is not configured. Set up the wallet in the UI first.');
    },
    signOut: async () => {},
    fetchWithPayment: fetch as WalletFetch,
    configureWallet: ({ projectId: nextProjectId, useMock: nextUseMock }) => {
      const trimmed = nextProjectId.trim();
      if (typeof window !== 'undefined') {
        if (trimmed) {
          window.localStorage.setItem(PROJECT_ID_STORAGE_KEY, trimmed);
        } else {
          window.localStorage.removeItem(PROJECT_ID_STORAGE_KEY);
        }
        window.localStorage.setItem(USE_MOCK_STORAGE_KEY, String(nextUseMock));
      }
      setProjectId(trimmed);
      setUseMock(nextUseMock);
    },
    clearWalletConfig: () => {
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(PROJECT_ID_STORAGE_KEY);
        window.localStorage.removeItem(USE_MOCK_STORAGE_KEY);
      }
      setProjectId('');
      setUseMock(false);
    },
  }), [projectId, useMock]);

  if (useMock) {
    return <WalletContext.Provider value={createMockSession(baseSession, setProjectId, setUseMock)}>{children}</WalletContext.Provider>;
  }

  return (
    <WalletContext.Provider value={baseSession}>
      {projectId ? (
        <CDPHooksProvider
          config={{
            projectId,
            useMock,
            ethereum: {
              createOnLogin: 'eoa',
            },
          }}
        >
          <CdpWalletBridge sessionBase={baseSession}>{children}</CdpWalletBridge>
        </CDPHooksProvider>
      ) : (
        children
      )}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  const session = useContext(WalletContext);
  if (!session) {
    return defaultSession;
  }
  return session;
}

export function formatWalletAddress(address: string | null) {
  if (!address) {
    return 'Not connected';
  }

  return abbreviate(address);
}
