import { useState, useCallback, useRef, useEffect } from 'react';

interface FilterState {
  selectedRoles: string[];
  selectedCategories: string[];
  selectedCapabilities: string[];
}

export const useStableFilter = (onFilterChange: (filter: FilterState) => void) => {
  // Use a ref to store the actual filter state to prevent re-renders
  const filterStateRef = useRef<FilterState>({
    selectedRoles: [],
    selectedCategories: [],
    selectedCapabilities: []
  });

  // Use a counter to force re-renders only when needed
  const [, forceUpdate] = useState(0);
  const forceRender = useCallback(() => {
    forceUpdate(prev => prev + 1);
  }, []);

  // Store the callback in a ref to avoid dependency issues
  const onFilterChangeRef = useRef(onFilterChange);
  onFilterChangeRef.current = onFilterChange;

  // Debounced notification to parent
  const notifyParent = useCallback(() => {
    const timeoutId = setTimeout(() => {
      onFilterChangeRef.current(filterStateRef.current);
    }, 0);
    return () => clearTimeout(timeoutId);
  }, []);

  const updateFilter = useCallback((updater: (prev: FilterState) => FilterState) => {
    const newState = updater(filterStateRef.current);
    filterStateRef.current = newState;
    forceRender();
    notifyParent();
  }, [forceRender, notifyParent]);

  const handleRoleChange = useCallback((roleName: string, checked: boolean) => {
    updateFilter(prev => ({
      ...prev,
      selectedRoles: checked 
        ? [...prev.selectedRoles, roleName]
        : prev.selectedRoles.filter(r => r !== roleName)
    }));
  }, [updateFilter]);

  const handleCategoryChange = useCallback((categoryName: string, checked: boolean) => {
    updateFilter(prev => ({
      ...prev,
      selectedCategories: checked 
        ? [...prev.selectedCategories, categoryName]
        : prev.selectedCategories.filter(c => c !== categoryName)
    }));
  }, [updateFilter]);

  const handleCapabilityChange = useCallback((capabilityName: string, checked: boolean) => {
    updateFilter(prev => ({
      ...prev,
      selectedCapabilities: checked 
        ? [...prev.selectedCapabilities, capabilityName]
        : prev.selectedCapabilities.filter(c => c !== capabilityName)
    }));
  }, [updateFilter]);

  const clearAllFilters = useCallback(() => {
    updateFilter(() => ({
      selectedRoles: [],
      selectedCategories: [],
      selectedCapabilities: []
    }));
  }, [updateFilter]);

  return {
    filterState: filterStateRef.current,
    handleRoleChange,
    handleCategoryChange,
    handleCapabilityChange,
    clearAllFilters
  };
};
