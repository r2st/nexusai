/**
 * Chat Sidebar Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock the sidebar component
const mockConversations = [
  { id: '1', title: 'First conversation', updatedAt: new Date().toISOString() },
  { id: '2', title: 'Second conversation', updatedAt: new Date().toISOString() },
  { id: '3', title: 'Third conversation', updatedAt: new Date().toISOString() },
];

interface SidebarProps {
  conversations?: typeof mockConversations;
  activeId?: string;
  onSelect?: (id: string) => void;
  onDelete?: (id: string) => void;
  onNewChat?: () => void;
  isCollapsed?: boolean;
}

const Sidebar = ({
  conversations = [],
  activeId,
  onSelect = vi.fn(),
  onDelete = vi.fn(),
  onNewChat = vi.fn(),
  isCollapsed = false,
}: SidebarProps) => (
  <aside data-testid="sidebar" className={isCollapsed ? 'w-16' : 'w-64'}>
    <button onClick={onNewChat} data-testid="new-chat">New Chat</button>
    <div data-testid="conversation-list">
      {conversations.map((conv) => (
        <div
          key={conv.id}
          data-testid={`conversation-${conv.id}`}
          className={activeId === conv.id ? 'active' : ''}
          onClick={() => onSelect(conv.id)}
        >
          <span>{conv.title}</span>
          <button onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}>Delete</button>
        </div>
      ))}
    </div>
  </aside>
);

describe('Sidebar', () => {
  it('renders sidebar container', () => {
    render(<Sidebar />);
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('renders new chat button', () => {
    render(<Sidebar />);
    expect(screen.getByTestId('new-chat')).toBeInTheDocument();
  });

  it('renders conversation list', () => {
    render(<Sidebar conversations={mockConversations} />);
    expect(screen.getByTestId('conversation-list')).toBeInTheDocument();
    expect(screen.getByText('First conversation')).toBeInTheDocument();
    expect(screen.getByText('Second conversation')).toBeInTheDocument();
  });

  it('calls onNewChat when new chat button is clicked', () => {
    const onNewChat = vi.fn();
    render(<Sidebar onNewChat={onNewChat} />);
    
    fireEvent.click(screen.getByTestId('new-chat'));
    expect(onNewChat).toHaveBeenCalled();
  });

  it('calls onSelect when conversation is clicked', () => {
    const onSelect = vi.fn();
    render(<Sidebar conversations={mockConversations} onSelect={onSelect} />);
    
    fireEvent.click(screen.getByTestId('conversation-1'));
    expect(onSelect).toHaveBeenCalledWith('1');
  });

  it('calls onDelete when delete button is clicked', () => {
    const onDelete = vi.fn();
    render(<Sidebar conversations={mockConversations} onDelete={onDelete} />);
    
    const deleteButtons = screen.getAllByText('Delete');
    fireEvent.click(deleteButtons[0]);
    expect(onDelete).toHaveBeenCalledWith('1');
  });

  it('highlights active conversation', () => {
    render(<Sidebar conversations={mockConversations} activeId="2" />);
    expect(screen.getByTestId('conversation-2')).toHaveClass('active');
  });

  it('renders collapsed state', () => {
    render(<Sidebar isCollapsed={true} />);
    expect(screen.getByTestId('sidebar')).toHaveClass('w-16');
  });

  it('renders expanded state', () => {
    render(<Sidebar isCollapsed={false} />);
    expect(screen.getByTestId('sidebar')).toHaveClass('w-64');
  });

  it('renders empty state when no conversations', () => {
    render(<Sidebar conversations={[]} />);
    const list = screen.getByTestId('conversation-list');
    expect(list.children.length).toBe(0);
  });
});

describe('Sidebar Interactions', () => {
  it('prevents event bubbling on delete', () => {
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    render(<Sidebar conversations={mockConversations} onSelect={onSelect} onDelete={onDelete} />);
    
    const deleteButtons = screen.getAllByText('Delete');
    fireEvent.click(deleteButtons[0]);
    
    expect(onDelete).toHaveBeenCalled();
    expect(onSelect).not.toHaveBeenCalled();
  });
});
