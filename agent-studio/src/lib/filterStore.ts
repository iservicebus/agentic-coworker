// Global filter state manager that's completely isolated from React re-renders
interface FilterState {
  selectedRoles: string[];
  selectedCategories: string[];
  selectedCapabilities: string[];
}

class FilterStore {
  private states: Map<string, FilterState> = new Map();
  private listeners: Map<string, Set<(state: FilterState) => void>> = new Map();

  private getStateKey(isAdminMode: boolean, agentId?: string): string {
    return isAdminMode ? 'admin' : `agent-${agentId || 'default'}`;
  }

  private getStateForKey(key: string): FilterState {
    if (!this.states.has(key)) {
      this.states.set(key, {
        selectedRoles: [],
        selectedCategories: [],
        selectedCapabilities: []
      });
    }
    return this.states.get(key)!;
  }

  getState(isAdminMode: boolean, agentId?: string): FilterState {
    const key = this.getStateKey(isAdminMode, agentId);
    return { ...this.getStateForKey(key) };
  }

  setState(newState: Partial<FilterState>, isAdminMode: boolean, agentId?: string) {
    const key = this.getStateKey(isAdminMode, agentId);
    const currentState = this.getStateForKey(key);
    const updatedState = { ...currentState, ...newState };
    this.states.set(key, updatedState);
    this.notifyListeners(key, updatedState);
  }

  updateRoles(roleName: string, checked: boolean, isAdminMode: boolean, agentId?: string) {
    const currentState = this.getState(isAdminMode, agentId);
    const newRoles = checked 
      ? [...currentState.selectedRoles, roleName]
      : currentState.selectedRoles.filter(r => r !== roleName);
    
    this.setState({ selectedRoles: newRoles }, isAdminMode, agentId);
  }

  updateCategories(categoryName: string, checked: boolean, isAdminMode: boolean, agentId?: string) {
    const currentState = this.getState(isAdminMode, agentId);
    const newCategories = checked 
      ? [...currentState.selectedCategories, categoryName]
      : currentState.selectedCategories.filter(c => c !== categoryName);
    
    this.setState({ selectedCategories: newCategories }, isAdminMode, agentId);
  }

  updateCapabilities(capabilityName: string, checked: boolean, isAdminMode: boolean, agentId?: string) {
    const currentState = this.getState(isAdminMode, agentId);
    const newCapabilities = checked 
      ? [...currentState.selectedCapabilities, capabilityName]
      : currentState.selectedCapabilities.filter(c => c !== capabilityName);
    
    this.setState({ selectedCapabilities: newCapabilities }, isAdminMode, agentId);
  }

  clearAll(isAdminMode: boolean, agentId?: string) {
    this.setState({
      selectedRoles: [],
      selectedCategories: [],
      selectedCapabilities: []
    }, isAdminMode, agentId);
  }

  subscribe(listener: (state: FilterState) => void, isAdminMode: boolean, agentId?: string) {
    const key = this.getStateKey(isAdminMode, agentId);
    
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    
    const keyListeners = this.listeners.get(key)!;
    keyListeners.add(listener);
    
    return () => {
      keyListeners.delete(listener);
      if (keyListeners.size === 0) {
        this.listeners.delete(key);
      }
    };
  }

  private notifyListeners(key: string, state: FilterState) {
    const keyListeners = this.listeners.get(key);
    if (keyListeners) {
      keyListeners.forEach(listener => {
        try {
          listener(state);
        } catch (error) {
          console.error('Filter store listener error:', error);
        }
      });
    }
  }
}

// Create a singleton instance
export const filterStore = new FilterStore();

// React hook to use the filter store
import { useState, useEffect } from 'react';

export const useFilterStore = (
  onFilterChange?: (state: FilterState) => void,
  isAdminMode: boolean = false,
  agentId?: string
) => {
  const [state, setState] = useState<FilterState>(filterStore.getState(isAdminMode, agentId));

  useEffect(() => {
    const unsubscribe = filterStore.subscribe((newState) => {
      setState(newState);
      if (onFilterChange) {
        onFilterChange(newState);
      }
    }, isAdminMode, agentId);

    return unsubscribe;
  }, [onFilterChange, isAdminMode, agentId]);

  return {
    filterState: state,
    updateRoles: (roleName: string, checked: boolean) => 
      filterStore.updateRoles(roleName, checked, isAdminMode, agentId),
    updateCategories: (categoryName: string, checked: boolean) => 
      filterStore.updateCategories(categoryName, checked, isAdminMode, agentId),
    updateCapabilities: (capabilityName: string, checked: boolean) => 
      filterStore.updateCapabilities(capabilityName, checked, isAdminMode, agentId),
    clearAll: () => filterStore.clearAll(isAdminMode, agentId)
  };
};
