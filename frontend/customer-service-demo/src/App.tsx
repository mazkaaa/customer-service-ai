import { useMutation } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import ChatInputForm from "./components/chat-input-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./components/ui/card";
import { cn } from "./lib/utils";

interface IConversation {
  id: string;
  from: "user" | "assistant";
  output: string;
  session_completed: boolean;
}

interface IStartChatResponse {
  session_id: string;
  response: string;
  output: string;
}

interface IContinueChatResponse {
  output: string;
  session_completed: boolean;
  session_id: string;
  ticket_id?: string;
}

interface IErrorResponse {
  detail: {
    message: string;
    output: string;
    session_id: string;
    session_completed: boolean;
  };
}

function App() {
  const [startConversation, setStartConversation] = useState(false);
  const [conversations, setConversations] = useState<IConversation[]>([]);

  const chatBoxRef = useRef<HTMLDivElement>(null);
  const [showTypingPlaceholder, setShowTypingPlaceholder] = useState(false);

  const addMessageToConversation = useCallback((message: IConversation) => {
    setConversations((prev) => [...prev, message]);
  }, []);

  const startChatMutation = useMutation({
    mutationFn: async (payload: { question: string }) => {
      const response = await fetch("http://localhost:8000/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: payload.question }),
      });
      if (!response.ok) {
        // return error response
        const errorData = (await response.json()) as IErrorResponse;
        throw errorData;
      }
      return response.json() as Promise<IStartChatResponse>;
    },
    onSuccess: (data) => {
      addMessageToConversation({
        id: crypto.randomUUID(),
        from: "assistant",
        output: data.output,
        session_completed: false,
      });
    },
    onError: (error: IErrorResponse) => {
      addMessageToConversation({
        id: crypto.randomUUID(),
        from: "assistant",
        output: error.detail.output,
        session_completed: error.detail.session_completed,
      });
    },
    onSettled: () => {
      setShowTypingPlaceholder(false);
    },
  });

  const continueChatMutation = useMutation({
    mutationFn: async (payload: { question: string; session_id: string }) => {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: payload.question,
          session_id: payload.session_id,
        }),
      });
      if (!response.ok) {
        const errorData = (await response.json()) as IErrorResponse;
        throw errorData;
      }
      return response.json() as Promise<IContinueChatResponse>;
    },
    onSuccess: (data) => {
      addMessageToConversation({
        id: crypto.randomUUID(),
        from: "assistant",
        output: data.output,
        session_completed: data.session_completed,
      });
    },
    onError: (error: IErrorResponse) => {
      addMessageToConversation({
        id: crypto.randomUUID(),
        from: "assistant",
        output: error.detail.output,
        session_completed: error.detail.session_completed,
      });
    },
    onSettled: () => {
      setShowTypingPlaceholder(false);
    },
  });

  useEffect(() => {
    if (conversations.length > 0 || showTypingPlaceholder) {
      chatBoxRef.current?.scrollTo({
        top: chatBoxRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [conversations, showTypingPlaceholder]);

  // make placeholderTypingRef show when mutation is loading (after some delay)
  useEffect(() => {
    let timeout: NodeJS.Timeout;
    if (startChatMutation.isPending || continueChatMutation.isPending) {
      timeout = setTimeout(() => {
        setShowTypingPlaceholder(true);
      }, 500); // show after 500ms
    }
    return () => {
      clearTimeout(timeout);
    };
  }, [startChatMutation.isPending, continueChatMutation.isPending]);

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center">
      <Card
        className={cn("w-sm", {
          "gap-2": !startConversation,
          "gap-6": startConversation,
        })}
      >
        <CardHeader>
          <CardTitle>Customer Support AI</CardTitle>
          <CardDescription>
            Ask any questions you have about our product
          </CardDescription>
        </CardHeader>
        <CardContent className="transition-all">
          <div
            ref={chatBoxRef}
            className={cn(
              "flex flex-col gap-4 overflow-y-auto transition-all duration-500 [&>div>ol]:list-decimal [&>div>ol]:pl-6 [&>ul]:list-disc [&>ul]:pl-6 [&>li]:mt-1",
              {
                "h-96": startConversation,
                "h-0": !startConversation,
              }
            )}
          >
            {conversations.map((item) => (
              <div
                key={item.id}
                className={cn(
                  "flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm",
                  item.from === "assistant"
                    ? "bg-muted"
                    : "bg-primary text-primary-foreground ml-auto"
                )}
              >
                <Markdown>{item.output}</Markdown>
              </div>
            ))}
            {(startChatMutation.isPending || continueChatMutation.isPending) &&
            showTypingPlaceholder ? (
              <div className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm bg-muted">
                <span className="italic text-muted-foreground">
                  Customer Support AI is typing...
                </span>
              </div>
            ) : null}
          </div>
        </CardContent>
        <CardFooter>
          <ChatInputForm
            isCompleted={
              conversations.length > 0 &&
              conversations[conversations.length - 1].session_completed
            }
            isEmpty={conversations.length === 0}
            isLoading={
              startChatMutation.isPending || continueChatMutation.isPending
            }
            onSubmit={(message) => {
              addMessageToConversation({
                id: crypto.randomUUID(),
                from: "user",
                output: message,
                session_completed: false,
              });

              if (
                (conversations.length === 0 && !startConversation) ||
                (conversations.length > 0 &&
                  conversations[conversations.length - 1].session_completed)
              ) {
                setStartConversation(true);
                startChatMutation.mutate({
                  question: message,
                });
              } else if (startChatMutation.isSuccess) {
                continueChatMutation.mutate({
                  question: message,
                  session_id: startChatMutation.data.session_id,
                });
              }
            }}
          />
        </CardFooter>
      </Card>
    </main>
  );
}

export default App;
