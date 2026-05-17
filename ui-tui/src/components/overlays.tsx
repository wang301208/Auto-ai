import React from 'react';
import { useStore } from '@nanostores/react';
import type { OverlayState } from '../types.js';
import { overlayAtom } from '../stores/overlayStore.js';
import { ApprovalOverlay } from './overlays/approvalOverlay.js';
import { ClarifyOverlay } from './overlays/clarifyOverlay.js';
import { SecretOverlay, SudoOverlay } from './overlays/authOverlay.js';
import { SessionPickerOverlay } from './overlays/sessionPickerOverlay.js';
import { ModelPickerOverlay } from './overlays/modelPickerOverlay.js';
import { ModelSetupOverlay } from './overlays/modelSetupOverlay.js';

export default function Overlays() {
  const overlay = useStore(overlayAtom);

  if (overlay.type === 'none') return null;

  switch (overlay.type) {
    case 'approval':
      return <ApprovalOverlay overlay={overlay} />;
    case 'clarify':
      return <ClarifyOverlay overlay={overlay} />;
    case 'secret':
      return <SecretOverlay overlay={overlay} />;
    case 'sudo':
      return <SudoOverlay overlay={overlay} />;
    case 'sessionPicker':
      return <SessionPickerOverlay overlay={overlay} />;
    case 'modelPicker':
      return <ModelPickerOverlay overlay={overlay} />;
    case 'modelSetup':
      return <ModelSetupOverlay overlay={overlay} />;
    default:
      return null;
  }
}

export { APPROVAL_CHOICES as approvalChoices } from '../constants.js';
