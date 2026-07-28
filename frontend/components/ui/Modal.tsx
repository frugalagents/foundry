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
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current();
      if (e.key !== 'Tab' || !panelRef.current) return;

      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) {
        e.preventDefault();
        panelRef.current.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    requestAnimationFrame(() => {
      const initial = panelRef.current?.querySelector<HTMLElement>(
        '[data-autofocus], input:not([disabled]), textarea:not([disabled]), button:not([disabled])',
      );
      (initial ?? panelRef.current)?.focus();
    });
    return () => {
      document.removeEventListener('keydown', onKey);
      previousFocus?.focus();
    };
  }, [open]);

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
              background: 'rgba(31,30,27,0.35)',
              backdropFilter: 'blur(2px)',
            }}
          />
          {/* Flex-centering wrapper: motion animates the panel's transform,
              so centering must NOT rely on transform (they'd conflict). */}
          <div
            style={{
              position: 'fixed', inset: 0, zIndex: 51,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: 16, pointerEvents: 'none',
            }}
          >
            <motion.div
              key="modal"
              ref={panelRef}
              role="dialog"
              aria-modal="true"
              aria-label={title}
              tabIndex={-1}
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 8 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              style={{
                pointerEvents: 'auto',
                width: sizeWidths[size],
                maxWidth: '100%',
                maxHeight: 'calc(100vh - 32px)',
                display: 'flex', flexDirection: 'column',
                overflow: 'hidden',
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
                  padding: '16px 20px', flexShrink: 0,
                  borderBottom: '1px solid var(--border-default)',
                }}
              >
                <h2 className="text-display" style={{ fontSize: 'var(--text-lg)', color: 'var(--text-primary)' }}>
                  {title}
                </h2>
                <button onClick={onClose} aria-label="Close" className="modal-close">
                  <X size={16} />
                </button>
              </div>
              <div style={{ padding: '20px', overflowY: 'auto' }}>{children}</div>
            </motion.div>
          </div>
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
