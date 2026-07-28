'use client';
import { AnimatePresence, motion } from 'framer-motion';
import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import type { ReactNode } from 'react';

type ModalSize = 'sm' | 'md' | 'lg';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  size?: ModalSize;
}

const sizeWidths: Record<ModalSize, string> = {
  sm: '400px',
  md: '560px',
  lg: '720px',
};

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Escape to close + focus the panel on open (basic focus management).
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    panelRef.current?.focus();
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            style={{
              position: 'fixed', inset: 0, zIndex: 50,
              background: 'rgba(0,0,0,0.6)',
              backdropFilter: 'blur(2px)',
            }}
          />
          <motion.div
            key="modal"
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            style={{
              position: 'fixed', top: '50%', left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 51,
              width: sizeWidths[size],
              maxWidth: 'calc(100vw - 32px)',
              maxHeight: 'calc(100vh - 64px)',
              overflow: 'auto',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-elevated)',
              outline: 'none',
            }}
          >
            <div
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '16px 20px',
                borderBottom: '1px solid var(--border-default)',
              }}
            >
              <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--text-primary)' }}>
                {title}
              </h2>
              <button
                onClick={onClose}
                aria-label="Close"
                className="modal-close"
              >
                <X size={16} />
              </button>
            </div>
            <div style={{ padding: '20px' }}>{children}</div>
          </motion.div>
          <style jsx>{`
            .modal-close {
              display: inline-flex; align-items: center; justify-content: center;
              width: 28px; height: 28px;
              background: none; border: none; cursor: pointer;
              color: var(--text-muted); border-radius: var(--radius-sm);
              transition: background 0.15s, color 0.15s;
            }
            .modal-close:hover { background: var(--bg-hover); color: var(--text-primary); }
            .modal-close:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
          `}</style>
        </>
      )}
    </AnimatePresence>
  );
}

export default Modal;
