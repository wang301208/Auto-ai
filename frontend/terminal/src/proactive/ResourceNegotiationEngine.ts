import type {
  ResourceNegotiation,
  NegotiationResult,
  SuggestionAction,
  ResourceAmount
} from '../types';
import { NegotiationStatus } from '../types';

export class ResourceNegotiationEngine {
  handleNegotiation(
    negotiation: ResourceNegotiation,
    userAction: SuggestionAction,
    negotiatedContent?: string
  ): NegotiationResult {
    const result: NegotiationResult = {
      negotiationId: negotiation.id,
      status: NegotiationStatus.PENDING,
      message: {
        zh: '协商处理中',
        en: 'Negotiation in progress'
      }
    };

    switch (userAction) {
      case 'confirm':
        result.status = NegotiationStatus.ACCEPTED;
        result.message = {
          zh: '资源请求已接受',
          en: 'Resource request accepted'
        };
        result.allocatedResources = negotiation.requestedAmount;
        break;

      case 'reject':
        result.status = NegotiationStatus.REJECTED;
        result.message = {
          zh: '资源请求已拒绝',
          en: 'Resource request rejected'
        };
        break;

      case 'negotiate':
        result.status = NegotiationStatus.MODIFIED;
        result.message = {
          zh: '资源请求已修改',
          en: 'Resource request modified'
        };
        break;

      default:
        result.status = NegotiationStatus.REJECTED;
        result.message = {
          zh: '无效的操作',
          en: 'Invalid action'
        };
    }

    return result;
  }
}

export const resourceNegotiationEngine = new ResourceNegotiationEngine();
